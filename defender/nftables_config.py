#!/usr/bin/env python3


import subprocess
import json
import os
import logging
import re  # <--- 新增：引入正则模块
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RLDefenseConfig:
    # 1. 全局流量限速 (pps)
    global_limit: int = 10000
    # 2. 单 IP 连接速率限制 (pps)
    single_ip_limit: int = 100
    # 3. 并发连接数限制 (count)
    conn_limit: int = 50
    # 4. 黑名单策略/封禁阈值 (pps)
    ban_threshold: int = 5
    
    PARAM_RANGES = {
        'global_limit': {'min': 1000, 'max': 100000, 'default': 10000},
        'single_ip_limit': {'min': 10, 'max': 5000, 'default': 100},
        'conn_limit': {'min': 10, 'max': 1000, 'default': 50},
        'ban_threshold': {'min': 1, 'max': 100, 'default': 5}
    }
    
    def validate(self) -> bool:
        for param, ranges in self.PARAM_RANGES.items():
            value = getattr(self, param)
            if not (ranges['min'] <= value <= ranges['max']):
                logger.warning(f"参数 {param}={value} 超出范围，将被限制")
                setattr(self, param, max(ranges['min'], min(value, ranges['max'])))
        return True

    def save(self, filepath: str = '/etc/nftables_defense_config.json'):
        with open(filepath, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, filepath: str = '/etc/nftables_defense_config.json') -> 'RLDefenseConfig':
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return cls(**json.load(f))
        return cls()


class NFTablesManager:
    def __init__(self, config: RLDefenseConfig = None):
        self.config = config or RLDefenseConfig()
        self.config.validate()
        self.config_file = '/etc/nftables_defense.conf'

    def generate_nftables_rules(self) -> str:
        c = self.config
        global_burst = int(c.global_limit * 1.3)
        single_ip_burst = int(c.single_ip_limit * 1.5)
        ban_time = 300 

        rules = [
            "#!/usr/sbin/nft -f",
            "",
            "flush ruleset",
            "",
            "table inet defense {",
            
            "    set blacklist { type ipv4_addr; flags timeout; }",
            f"    set auto_banned {{ type ipv4_addr; flags timeout; timeout {ban_time}s; }}",
            
            "    counter tp_count {}",
            "    counter fp_count {}",
            "    counter tn_count {}",
            "    counter fn_count {}",
            "",
            "    chain handle_drop {",
            "        ip ttl le 40 counter name fp_count drop",
            "        counter name tp_count drop",
            "    }",
            "",
            "    chain handle_accept {",
            "        ip ttl le 40 counter name tn_count accept",
            "        counter name fn_count accept",
            "    }",
            "",
            "    chain input {",
            "        type filter hook input priority filter; policy accept;",
            "        iif lo accept",
            "        ct state established,related accept",
            "        tcp dport { 22, 5000 } accept",
            "    }",
            "",
            "    chain forward {",
            "        type filter hook forward priority filter; policy drop;",
            "        ip saddr @blacklist jump handle_drop",
            "        ip saddr @auto_banned jump handle_drop",
            f"        limit rate over {c.global_limit}/second burst {global_burst} packets jump handle_drop",
            f"        ct count over {c.conn_limit} jump handle_drop",
            f"        tcp flags syn meter ban_meter {{ ip saddr limit rate over {c.ban_threshold}/second }} add @auto_banned {{ ip saddr }} jump handle_drop",
            f"        meta l4proto udp meter ban_meter_udp {{ ip saddr limit rate over {c.ban_threshold}/second }} add @auto_banned {{ ip saddr }} jump handle_drop",
            f"        tcp flags syn meter per_ip_syn {{ ip saddr limit rate over {c.single_ip_limit}/second burst {single_ip_burst} packets }} jump handle_drop",
            f"        meta l4proto udp meter per_ip_udp {{ ip saddr limit rate over {c.single_ip_limit}/second burst {single_ip_burst} packets }} jump handle_drop",
            "        ct state established,related accept",
            "        ip protocol tcp jump handle_accept",
            "        ip protocol udp jump handle_accept",
            "        ip protocol icmp jump handle_accept",
            "    }",
            "",
            "    chain postrouting {",
            "        type nat hook postrouting priority srcnat; policy accept;",
            "        oifname \"eth1\" masquerade",
            "    }",    # add NAT rule 
            "}"
        ]
        return "\n".join(rules)

    def apply_rules(self) -> bool:
        try:
            content = self.generate_nftables_rules()
            with open(self.config_file, 'w') as f:
                f.write(content)
            res = subprocess.run(['nft', '-f', self.config_file], capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"Rules apply failed: {res.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Apply exception: {e}")
            return False

    def get_statistics(self) -> dict:
        """获取统计信息 (正则修复版)"""
        stats = {
            "config": asdict(self.config), 
            "counters": {},
            "metrics": {"precision": 0.0, "recall": 0.0, "f1_score": 0.0}
        }
        
        try:
            # 1. 获取规则集 (包含 counters)
            cmd = ['nft', 'list', 'counters', 'table', 'inet', 'defense']
            res = subprocess.run(cmd, capture_output=True, text=True)
            
            # logger.info(f"NFT counters output:\n{res.stdout}")
            
            if res.returncode == 0:
                # 使用正则表达式提取，无视换行符
                # 匹配模式：counter + 空格 + 名字 + 任意字符(跨行) + packets + 空格 + 数字
                pattern = re.compile(r'counter\s+(\w+)\s+\{[^}]*packets\s+(\d+)', re.DOTALL)
                matches = pattern.findall(res.stdout)
                
                logger.info(f"Regex matches: {matches}")
                
                for name, packets in matches:
                    stats['counters'][name] = int(packets)
            else:
                logger.error(f"NFT command failed: {res.stderr}")
            
            # 2. 读取黑名单数量
            cmd_set = ['nft', 'list', 'set', 'inet', 'defense', 'blacklist']
            res_set = subprocess.run(cmd_set, capture_output=True, text=True)
            if res_set.returncode == 0:
                 count = res_set.stdout.count('elements = {') 
                 if count == 0 and 'elements = {' in res_set.stdout:
                     count = res_set.stdout.count(',') + 1
                 stats['counters']['blacklist_count'] = count

            # 3. 计算 F1 Score
            tp = stats['counters'].get('tp_count', 0)
            fp = stats['counters'].get('fp_count', 0)
            fn = stats['counters'].get('fn_count', 0)
            
            epsilon = 1e-9
            precision = tp / (tp + fp + epsilon)
            recall = tp / (tp + fn + epsilon)
            f1 = 2 * (precision * recall) / (precision + recall + epsilon)
            
            stats['metrics']['precision'] = round(precision, 4)
            stats['metrics']['recall'] = round(recall, 4)
            stats['metrics']['f1_score'] = round(f1, 4)

        except Exception as e:
            logger.error(f"Get stats failed: {e}")
            
        return stats

    def get_all_params(self) -> dict:
        return asdict(self.config)

    def batch_update_params(self, params: dict) -> bool:
        try:
            for k, v in params.items():
                if hasattr(self.config, k):
                    setattr(self.config, k, int(v))
            self.config.validate()
            return self.apply_rules()
        except Exception as e:
            logger.error(f"Update failed: {e}")
            return False
    
    def get_param_ranges(self) -> dict:
        return RLDefenseConfig.PARAM_RANGES
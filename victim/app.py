from flask import Flask, request, jsonify
import time, math

app = Flask(__name__)


@app.route("/")
def index():
    # 简单返回ok
    return "ok\n"


@app.route('/status')
def status():
    # delay 参数，单位毫秒，默认 100ms
    def busy_ms(ms):
        end = time.time() + ms/1000.0
        x = 0.0
        while time.time() < end:
            x += math.sqrt(12345.6789)
        return x

    try:
        delay_ms = int(request.args.get('delay', '100'))
    except:
        delay_ms = 100
    # time.sleep(delay_ms / 1000.0)
    busy_ms(delay_ms)
    return jsonify({"status": "ok", "delay_ms": delay_ms})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)

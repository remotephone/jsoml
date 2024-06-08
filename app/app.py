import json
import logging
import toml
import yaml

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


def log_and_respond(level, message, data=""):
    logging.log(level, message)
    return jsonify({"message": message, "data": data})


def convert_data(input_data, input_format, output_format):
    format_functions = {
        "JSON": (json.loads, lambda data: json.dumps(data, indent=4)),
        "TOML": (toml.loads, toml.dumps),
        "YAML": (yaml.safe_load, yaml.safe_dump),
    }
    try:
        load, dump = (
            format_functions[input_format][0],
            format_functions[output_format][1],
        )
        return dump(load(input_data))
    except Exception as e:
        return log_and_respond(logging.ERROR, f"Conversion error: {str(e)}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    input_data = request.form["input_data"]
    input_format = request.form["input_format"]
    output_format = request.form["output_format"]
    logging.info(f"Conversion requested: {input_format} to {output_format}")
    output_data = convert_data(input_data, input_format, output_format)
    # if output_format == 'JSON':
    #     # ensure JSON is pretty printed
    #     return jsonify({'output_data': json.dumps(json.loads(output_data), indent=4)})
    return jsonify({"output_data": output_data})


@app.route("/check_format", methods=["POST"])
def check_format():
    input_text = request.data.decode("utf-8")
    logging.debug(f"Checking format for input of length : {len(input_text)}...")

    # Function to try parsing with the given format
    def try_parse(parser, format_name, error_log_message):
        try:
            parser(input_text)
            logging.info(f"Input is valid {format_name}")
            return (
                jsonify(
                    {"format": format_name, "message": f"Valid {format_name} format"}
                ),
                True,
            )
        except Exception as e:
            logging.warning(f"{error_log_message}: {str(e)}")
            return None, False

    # Try TOML
    result, success = try_parse(toml.loads, "TOML", "TOML decoding error")
    if success:
        return result

    # Try JSON
    result, success = try_parse(json.loads, "JSON", "JSON decoding error")
    if success:
        return result

    # Try YAML
    result, success = try_parse(yaml.safe_load, "YAML", "YAML decoding error")
    if success:
        return result

    # If all parsers fail
    return jsonify({"format": "Unknown", "message": "Format could not be determined"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

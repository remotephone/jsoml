import io
import json
import logging

import toml
import yaml

from flask import Flask, jsonify, render_template, request

# 1. Imports and Initial Setup
app = Flask(__name__)
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


# 2. Utility Functions
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


# 3. Navigation Routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/jsoml")
def tool1():
    return render_template("jsoml.html")


@app.route("/traefik_cop")
def tool2():
    return render_template("traefik_cop.html")


# 4. Tool Logic Routes
@app.route("/convert", methods=["POST"])
def convert():
    input_data = request.form["input_data"]
    input_format = request.form["input_format"]
    output_format = request.form["output_format"]
    logging.info(f"Conversion requested: {input_format} to {output_format}")
    output_data = convert_data(input_data, input_format, output_format)
    return jsonify({"output_data": output_data})


@app.route("/check_format", methods=["POST"])
def check_format():
    input_text = request.data.decode("utf-8")
    logging.debug(f"Checking format for input of length : {len(input_text)}...")

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

    # Try parsing in order: TOML, JSON, YAML
    for format_name, parser, error_message in [
        ("TOML", toml.loads, "TOML decoding error"),
        ("JSON", json.loads, "JSON decoding error"),
        ("YAML", yaml.safe_load, "YAML decoding error"),
    ]:
        result, success = try_parse(parser, format_name, error_message)
        if success:
            return result
    return jsonify({"format": "Unknown", "message": "Format could not be determined"})


@app.route("/traefik_cop_work", methods=["POST"])
def modify_docker_compose():
    try:
        data = request.json
        options = data.get("options", {})
        logging.info("Received request with options: %s", data)
        # Assuming the input box content is sent under the key 'input_box_content'
        input_box_content = options.get("input_box_content", "")
        logging.info(
            f"Received request with input box content: {len(input_box_content)}",
            input_box_content,
        )
        domain_name = data.get("domain_name", "example.com")
        # Load the YAML to ensure it's valid and to process it
        try:
            docker_compose = yaml.safe_load(input_box_content)
            if docker_compose is None:
                return jsonify({"error": "No valid docker-compose file submitted"}), 400
        except yaml.YAMLError:
            return jsonify({"error": "No valid docker-compose file submitted"}), 400
        logging.info("Received request with options: %s", options)

        for service_name, service_details in docker_compose["services"].items():
            logging.info("Modifying service: %s", service_name)
            labels_set = set(service_details.get("deploy", {}).get("labels", []))
            volumes_set = set(service_details.get("volumes", []))
            domain_name = data.get(
                "domain_name", "example.com"
            )  # Get the domain name from the request, default to 'example.com'

            # Update labels based on options
            if options.get("traefikHTTP"):
                labels_set.update(
                    [
                        "traefik.enable=true",
                        "traefik.constraint-label=traefik-public",
                        f"traefik.http.routers.{service_name}.rule=Host(`{service_name}.{domain_name}`)",
                        f"traefik.http.services.{service_name}.loadbalancer.server.port=<PORT>",
                    ]
                )
            if options.get("traefikHTTPS"):
                labels_set.update(
                    [
                        "traefik.enable=true",
                        "traefik.constraint-label=traefik-public",
                        f"traefik.http.routers.{service_name}.rule=Host(`{service_name}.{domain_name}`)",
                        f"traefik.http.services.{service_name}.loadbalancer.server.port=<PORT>",
                        "traefik.http.routers.{service_name}.tls=true",
                        "traefik.http.routers.{service_name}.tls.certresolver=le",
                    ]
                )
            if options.get("traefikNoAuth"):
                labels_set.update(
                    [
                        "traefik.enable=true",
                        "traefik.constraint-label=traefik-public",
                        f"traefik.http.routers.{service_name}.middlewares=no-auth",
                        f"traefik.http.routers.{service_name}-noauth.rule=Host(`{service_name}-noauth.{domain_name}`)",
                        "traefik.http.routers.{service_name}-noauth.entrypoints=noauth",
                    ]
                )
            # Update volumes based on options
            if options.get("volume"):
                volumes_set.add("/path/to/volume:/path/to/mount")
            if options.get("volumeNFS"):
                volumes_set.add("/path/to/volume:/path/to/mount:shared")
                docker_compose.setdefault("volumes", {}).update(
                    {
                        f"{service_name}-data": {
                            "driver": "local",
                            "driver_opts": {
                                "type": "nfs",
                                "o": "addr=<IP>,nfsvers=4,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2",
                                "device": ":/volume1/<volume_name>",
                            },
                        }
                    }
                )

            # Ensure the 'deploy' and 'volumes' keys are updated or added to the service details
            service_details.setdefault("deploy", {})["labels"] = list(labels_set)
            service_details["volumes"] = list(volumes_set)

        logging.info("Successfully modified docker-compose file.")
        output_yaml = custom_yaml_dump(docker_compose)
        return jsonify({"output_data": output_yaml})

    except Exception as e:
        logging.error("Failed to modify docker-compose file: %s", str(e))
        return jsonify({"error": "Internal server error"}), 500


def custom_yaml_dump(docker_compose):
    ordered_services = {}
    for service_name, service_details in docker_compose["services"].items():
        # Reorder keys for each service
        ordered_service = {}
        key_order = ["image", "deploy", "volumes"]
        for key in key_order:
            if key in service_details:
                ordered_service[key] = service_details[key]
        ordered_services[service_name] = ordered_service

    # Replace the original services with the ordered ones
    docker_compose["services"] = ordered_services

    # Use a custom dumper or manipulate the YAML string directly for NFS volumes formatting
    yaml_str = yaml.dump(docker_compose, default_flow_style=False, sort_keys=False)

    # Insert extra blank lines for NFS volumes (simple example, might need adjustment)
    yaml_str = yaml_str.replace("driver_opts:", "driver_opts:\n\n")

    return yaml_str


# 5. Main Block
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

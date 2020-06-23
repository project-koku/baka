#
# Copyright 2018 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Cost and Usage Generator CLI."""
import argparse
import calendar
import datetime
import logging
import os

import yaml
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
from nise import __version__
from nise.report import aws_create_report
from nise.report import azure_create_report
from nise.report import gcp_create_report
from nise.report import ocp_create_report
from nise.yaml_gen import add_yaml_parser_args
from nise.yaml_gen import yaml_main

LOG = logging.getLogger(__name__)


class NiseError(Exception):
    """A Nise Exception class."""


def valid_date(date_string):
    """Create date from date string."""
    try:
        valid = datetime.datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError:
        msg = f"{date_string} is an unsupported date format."
        raise argparse.ArgumentTypeError(msg)
    return valid


def today():
    """Create the date of today."""
    return datetime.datetime.now().replace(microsecond=0, second=0, minute=0)


def add_aws_parser_args(parser):
    """Add AWS sub-parser args."""
    parser.add_argument(
        "--aws-s3-bucket-name",
        metavar="BUCKET_NAME",
        dest="aws_bucket_name",
        required=False,
        help="AWS S3 bucket to place the data.",
    )
    parser.add_argument(
        "--aws-s3-report-name",
        metavar="COST_REPORT_NAME",
        dest="aws_report_name",
        required=False,
        help="Directory path to store data in the S3 bucket.",
    )
    parser.add_argument(
        "--aws-s3-report-prefix",
        metavar="PREFIX_NAME",
        dest="aws_prefix_name",
        required=False,
        help="Directory path to store data in the S3 bucket.",
    )
    parser.add_argument(
        "--aws-finalize",
        metavar="FINALIZE_REPORT",
        dest="aws_finalize_report",
        choices=["copy", "overwrite"],
        required=False,
        help="""Whether to generate finalized report data.
                            Can be either \'copy\' to produce a second finalized file locally
                            or \'overwrite\' to finalize the normal report files.
                            """,
    )


def add_azure_parser_args(parser):
    """Add Azure sub-parser args."""
    parser.add_argument(
        "--azure-container-name",
        metavar="AZURE_CONTAINER_NAME",
        dest="azure_container_name",
        required=False,
        help="Azure container to place the data.",
    )
    parser.add_argument(
        "--azure-report-name",
        metavar="AZURE_COST_REPORT_NAME",
        dest="azure_report_name",
        required=False,
        help="Directory path to store data in the bucket.",
    )
    parser.add_argument(
        "--azure-report-prefix",
        metavar="AZURE_PREFIX_NAME",
        dest="azure_prefix_name",
        required=False,
        help="Directory path to store data in the bucket.",
    )
    parser.add_argument(
        "--azure-account-name",
        metavar="AZURE_ACCOUNT_NAME",
        dest="azure_account_name",
        required=False,
        default=os.getenv("AZURE_STORAGE_ACCOUNT"),
        help="Azure container to place the data.",
    )


def add_gcp_parser_args(parser):
    """Add GCP sub-parser args."""
    parser.add_argument(
        "--gcp-report-prefix",
        metavar="GCP_REPORT_PREFIX",
        dest="gcp_report_prefix",
        required=False,
        help="GCP Billing Report Prefix.",
    )
    parser.add_argument(
        "--gcp-bucket-name",
        metavar="GCP_BUCKET_NAME",
        dest="gcp_bucket_name",
        required=False,
        help="GCP storage account to place the data.",
    )


def add_ocp_parser_args(parser):
    """Add OCP sub-parser args."""
    parser.add_argument(
        "--ocp-cluster-id",
        metavar="OCP_CLUSTER_ID",
        dest="ocp_cluster_id",
        required=False,
        help="Cluster identifier for usage data.",
    )
    parser.add_argument(
        "--insights-upload",
        metavar="UPLOAD_ENDPOINT",
        dest="insights_upload",
        required=False,
        help="URL for Insights Upload Service.",
    )


def create_parser():
    """Create the parser for incoming data."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    report_parser = subparsers.add_parser("report", help="Generate fake cost usage reports.")
    yaml_parser = subparsers.add_parser("yaml", help="Generate a yaml for creating cost usage reports.")

    add_yaml_parser_args(yaml_parser)

    parent_parser = argparse.ArgumentParser()
    parent_parser.add_argument(
        "-s",
        "--start-date",
        metavar="YYYY-MM-DD",
        dest="start_date",
        required=False,
        type=valid_date,
        help="Date to start generating data (YYYY-MM-DD)",
    )
    parent_parser.add_argument(
        "-e",
        "--end-date",
        metavar="YYYY-MM-DD",
        dest="end_date",
        required=False,
        type=valid_date,
        default=today(),
        help="Date to end generating data (YYYY-MM-DD). Default is today.",
    )
    parent_parser.add_argument(
        "--file-row-limit",
        dest="row_limit",
        required=False,
        type=int,
        default=100000,
        help="Maximum number of lines per report file. Default is 100000.",
    )
    parent_parser.add_argument(
        "--static-report-file", dest="static_report_file", required=False, help="Generate static data based on yaml."
    )
    parent_parser.add_argument(
        "-w",
        "--write-monthly",
        dest="write_monthly",
        action="store_true",
        required=False,
        help="Writes the monthly files.",
    )

    report_subparser = report_parser.add_subparsers(dest="provider")
    aws_parser = report_subparser.add_parser(
        "aws", parents=[parent_parser], add_help=False, description="The AWS parser", help="create the AWS reports"
    )
    azure_parser = report_subparser.add_parser(
        "azure",
        parents=[parent_parser],
        add_help=False,
        description="The Azure parser",
        help="create the Azure reports",
    )
    gcp_parser = report_subparser.add_parser(
        "gcp", parents=[parent_parser], add_help=False, description="The GCP parser", help="create the GCP reports"
    )
    ocp_parser = report_subparser.add_parser(
        "ocp", parents=[parent_parser], add_help=False, description="The OCP parser", help="create the OCP reports"
    )

    add_aws_parser_args(aws_parser)
    add_azure_parser_args(azure_parser)
    add_gcp_parser_args(gcp_parser)
    add_ocp_parser_args(ocp_parser)

    return parser


def _get_aws_options(options):
    """Obtain all the aws options.

    Args:
        options (Dict): dictionary of arguments.
    Returns:
        aws_bucket_name (string): AWS bucket name
        aws_report_name (string): AWS report name
        aws_prefix_name (string): AWS report prefix
        aws_finalize_report (string): AWS finalize choice

    """
    aws_bucket_name = options.get("aws_bucket_name")
    aws_report_name = options.get("aws_report_name")
    aws_prefix_name = options.get("aws_prefix_name")
    aws_finalize_report = options.get("aws_finalize_report")
    return (aws_bucket_name, aws_report_name, aws_prefix_name, aws_finalize_report)


def _get_azure_options(options):
    """Obtain all the azure options.

    Args:
        options (Dict): dictionary of arguments.
    Returns:
        azure_container_name (string): Azure storage account name
        azure_report_name (string): Azure report name
        azure_prefix_name (string): Azure report prefix
        azure_account_name (string): Azure account name

    """
    azure_container_name = options.get("azure_container_name")
    azure_report_name = options.get("azure_report_name")
    azure_prefix_name = options.get("azure_prefix_name")
    azure_account_name = options.get("azure_account_name")
    return (azure_container_name, azure_report_name, azure_prefix_name, azure_account_name)


def _get_ocp_options(options):
    """Obtain all the ocp options.

    Args:
        options (Dict): dictionary of arguments.
    Returns:
        ocp_cluster_id (string): OCP cluster id

    """
    ocp_cluster_id = options.get("ocp_cluster_id")
    insights_upload = options.get("insights_upload")
    return (ocp_cluster_id, insights_upload)


def _get_gcp_options(options):
    """Obtain all the GCP options.

    Args:
        options (Dict): dictionary of arguments.
    Returns:
        gcp_report_prefix (string): GCP storage account name

    """
    gcp_report_prefix = options.get("gcp_report_prefix")
    gcp_bucket_name = options.get("gcp_bucket_name")
    return gcp_report_prefix, gcp_bucket_name


def _validate_aws_arguments(parser, options):
    """Validate aws argument combination.

    Args:
        parser (Object): ArgParser parser.
        options (Dict): dictionary of arguments.
    Raises:
        (ParserError): If combination is invalid.

    """
    aws_valid = False

    aws_bucket_name, aws_report_name, _, _ = _get_aws_options(options)
    if aws_bucket_name and aws_report_name:
        aws_valid = True
    elif not (aws_bucket_name or aws_report_name):
        aws_valid = True
    if not aws_valid:
        msg = "Both {} and {} must be supplied, if one is provided."
        msg = msg.format("--aws-s3-bucket-name", "--aws-s3-report-name")
        parser.error(msg)
    return aws_valid


def _validate_azure_arguments(parser, options):
    """Validate azure argument combination.

    Args:
        parser (Object): ArgParser parser.
        options (Dict): dictionary of arguments.
    Raises:
        (ParserError): If combination is invalid.

    """
    azure_valid = False

    azure_container_name, azure_report_name, _, _ = _get_azure_options(options)
    if azure_container_name and azure_report_name:
        azure_valid = True
    elif not (azure_container_name or azure_report_name):
        azure_valid = True
    if not azure_valid:
        msg = "Both {} and {} must be supplied, if one is provided."
        msg = msg.format("--azure-container-name", "--azure-report-name")
        parser.error(msg)
    return azure_valid


def _validate_ocp_arguments(parser, options):
    """Validate ocp argument combination.

    Args:
        parser (Object): ArgParser parser.
        options (Dict): dictionary of arguments.
    Raises:
        (ParserError): If combination is invalid.

    """
    ocp_valid = False

    ocp_cluster_id, insights_upload = _get_ocp_options(options)
    if ocp_cluster_id is None:
        msg = "{} must be supplied."
        msg = msg.format("--ocp-cluster-id")
        parser.error(msg)
    elif insights_upload is not None and not os.path.isdir(insights_upload):
        insights_user = os.environ.get("INSIGHTS_USER")
        insights_password = os.environ.get("INSIGHTS_PASSWORD")
        insights_account_id = os.environ.get("INSIGHTS_ACCOUNT_ID")
        insights_org_id = os.environ.get("INSIGHTS_ORG_ID")
        if (insights_account_id is None or insights_org_id is None) and (
            insights_user is None or insights_password is None
        ):
            msg = (
                "The environment must have \nINSIGHTS_USER and "
                "INSIGHTS_PASSWORD or\nINSIGHTS_ACCOUNT_ID and INSIGHTS_ORG_ID"
                "defined when {} {} is supplied."
            )
            msg = msg.format("--insights-upload", insights_upload)
            parser.error(msg)
        # Either set of acceptable credentials are acceptable
        ocp_valid = True
    else:
        ocp_valid = True
    return ocp_valid


def _validate_gcp_arguments(parser, options):
    """Validate aws argument combination.

    Args:
        parser (Object): ArgParser parser.
        options (Dict): dictionary of arguments.
    Raises:
        (ParserError): If combination is invalid.

    """
    return True


def _validate_provider_inputs(parser, options):
    """Validate provider inputs.

    Args:
        parser (Object): ArgParser parser.
        options (Dict): dictionary of arguments.
    Raises:
        (ParserError): If combination is invalid.

    """
    valid_inputs = False
    provider_type = options.get("provider")
    VALIDATOR_MAP = {
        "aws": _validate_aws_arguments,
        "azure": _validate_azure_arguments,
        "gcp": _validate_gcp_arguments,
        "ocp": _validate_ocp_arguments,
    }

    if VALIDATOR_MAP.get(provider_type):
        func = VALIDATOR_MAP.get(provider_type)
        valid_inputs = func(parser, options)
    else:
        msg = "One of {}, {}, {}, or {} must be supplied to generate a report."
        msg = msg.format("aws", "azure", "ocp", "gcp")
        parser.error(msg)
    return (valid_inputs, provider_type)


def load_yaml_file(filename):
    """Local data from yaml file."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f'Cannot find file "{filename}"')
    yamlfile = None
    if filename:
        try:
            with open(filename, "r+") as yaml_file:
                yamlfile = yaml.safe_load(yaml_file)
        except TypeError:
            yamlfile = yaml.safe_load(filename)
    return yamlfile


def _load_static_report_data(options):
    """Validate/load and set start_date if static file is provided."""
    if not options.get("static_report_file"):
        return
    LOG.info("Loading static data...")
    aws_tags = set()
    start_dates = []
    end_dates = []
    static_report_data = load_yaml_file(options.get("static_report_file"))
    for generator_dict in static_report_data.get("generators"):
        for _, attributes in generator_dict.items():
            generated_start_date = calculate_start_date(attributes.get("start_date"))
            start_dates.append(generated_start_date)

            if attributes.get("end_date"):
                generated_end_date = calculate_end_date(generated_start_date, attributes.get("end_date"))
            else:
                generated_end_date = today()
            if options.get("provider") == "azure":
                generated_end_date += datetime.timedelta(hours=24)
            else:
                generated_end_date = generated_end_date.replace(hour=23, minute=59)
            end_dates.append(generated_end_date)

            attributes["start_date"] = str(generated_start_date)
            attributes["end_date"] = str(generated_end_date)

            if options.get("provider") == "aws":
                aws_tags.update(attributes.get("tags", {}).keys())

    options["start_date"] = min(start_dates)
    latest_date = max(end_dates)
    last_day_of_month = calendar.monthrange(year=latest_date.year, month=latest_date.month)[1]
    options["end_date"] = latest_date.replace(day=last_day_of_month, hour=0, minute=0)
    options["static_report_data"] = static_report_data

    if options.get("provider") == "aws" and aws_tags:
        options["aws_tags"] = aws_tags

    return True


def calculate_start_date(start_date):
    """Return a datetime for the start date."""
    if start_date == "last_month":
        generated_start_date = today().replace(day=1, hour=0, minute=0, second=0) + relativedelta(months=-1)
    elif start_date == "today":
        generated_start_date = today().replace(hour=0, minute=0, second=0)
    elif start_date and isinstance(start_date, datetime.date):
        generated_start_date = datetime.datetime.fromordinal(start_date.toordinal())
    elif start_date:
        generated_start_date = date_parser.parse(start_date)
    else:
        generated_start_date = today().replace(day=1, hour=0, minute=0, second=0)
    return generated_start_date


def calculate_end_date(start_date, end_date):
    """Return a datetime for the end date."""
    try:
        if end_date == "last_month":
            generated_end_date = today().replace(day=1, hour=0, minute=0, second=0) + relativedelta(months=-1)
        elif end_date == "today":
            generated_end_date = today().replace(hour=0, minute=0, second=0)
        elif end_date and isinstance(end_date, datetime.date):
            generated_end_date = datetime.datetime.fromordinal(end_date.toordinal())
        else:
            generated_end_date = date_parser.parse(end_date)
    except TypeError:
        offset = end_date
        offset_date = start_date + relativedelta(days=offset)
        if offset_date.month > start_date.month:
            generated_end_date = offset_date
        else:
            generated_end_date = min(start_date + relativedelta(days=offset), today())
    if generated_end_date < start_date:
        raise ValueError("Static yaml error: End date must be after start date.")
    return generated_end_date


def fix_dates(options, provider_type):
    """Correct any unique dates."""
    # Azure end_date is always the following day
    if provider_type == "azure":
        options["end_date"] += relativedelta(days=1)


def run(provider_type, options):
    """Run nise."""
    static_data_bool = _load_static_report_data(options)
    if not options.get("start_date"):
        raise NiseError("'start_date' is required in static files.")
    if not static_data_bool:
        fix_dates(options, provider_type)

    LOG.info("Creating reports...")
    if provider_type == "aws":
        aws_create_report(options)
    elif provider_type == "azure":
        azure_create_report(options)
    elif provider_type == "ocp":
        ocp_create_report(options)
    elif provider_type == "gcp":
        gcp_create_report(options)


def main():
    """Run data generation program."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s")
    parser = create_parser()
    args = parser.parse_args()
    if not args.command:
        parser.error('"yaml" or "report" argument must be specified')
    elif args.command == "yaml":
        yaml_main(args)
        return
    options = vars(args)

    if not (options.get("start_date") or options.get("static_report_file")):
        parser.error("the following arguments are required: -s, --start-date")

    _, provider_type = _validate_provider_inputs(parser, options)

    run(provider_type, options)


if __name__ == "__main__":
    main()

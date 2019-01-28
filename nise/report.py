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
"""Module responsible for generating the cost and usage report."""
import calendar
import copy
import csv
import gzip
import importlib
import os
import random
import shutil
import string
import tarfile
from datetime import datetime
from tempfile import NamedTemporaryFile, gettempdir
from uuid import uuid4

import requests
from dateutil import parser
from dateutil.relativedelta import relativedelta
from faker import Faker

from nise.copy import copy_to_local_dir
from nise.extract import extract_payload
from nise.generators.aws import (AWS_COLUMNS,
                                 DataTransferGenerator,
                                 EBSGenerator,
                                 EC2Generator,
                                 S3Generator)
from nise.generators.ocp import (OCPGenerator,
                                 OCP_COLUMNS)
from nise.manifest import aws_generate_manifest, ocp_generate_manifest
from nise.upload import upload_to_s3


def create_temporary_copy(path, temp_file_name, temp_dir_name='None'):
    """Create temporary copy of a file."""
    temp_dir = gettempdir()
    if temp_dir_name:
        new_dir = os.path.join(temp_dir, temp_dir_name)
        if not os.path.exists(new_dir):
            os.mkdir(new_dir)
        temp_path = os.path.join(new_dir, temp_file_name)
    else:
        temp_path = os.path.join(temp_dir, temp_file_name)
    shutil.copy2(path, temp_path)
    return temp_path


def _write_csv(output_file, data, header):
    """Output csv file data."""
    with open(output_file, 'w') as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def _gzip_report(report_path):
    """Compress the report."""
    t_file = NamedTemporaryFile(mode='wb', suffix='.csv.gz', delete=False)
    with open(report_path, 'rb') as f_in, gzip.open(t_file.name, 'wb') as f_out:
        f_out.write(f_in.read())
    return t_file.name


def _tar_gzip_report(temp_dir):
    """Compress the report and manifest to tarfile."""
    t_file = NamedTemporaryFile(mode='w', suffix='.tar.gz', delete=False)

    with tarfile.open(t_file.name, 'w:gz') as tar:
        tar.add(temp_dir, arcname=os.path.sep)

    return t_file.name


def _write_manifest(data):
    """Write manifest file to temp location.

    Args:
        data    (String): data to store
    Returns:
        (String): Path to temporary file
    """
    t_file = NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    t_file.write(data)
    t_file.flush()
    return t_file.name


def aws_route_file(bucket_name, bucket_file_path, local_path):
    """Route file to either S3 bucket or local filesystem."""
    if os.path.isdir(bucket_name):
        copy_to_local_dir(bucket_name,
                          local_path,
                          bucket_file_path,)
    else:
        upload_to_s3(bucket_name,
                     bucket_file_path,
                     local_path)


def ocp_route_file(insights_upload, local_path):
    """Route file to either Upload Service or local filesystem."""
    if os.path.isdir(insights_upload):
        extract_payload(insights_upload,
                        local_path)
    else:
        with open(local_path, 'rb') as upload_file:
            insights_user = os.environ.get('INSIGHTS_USER')
            insights_password = os.environ.get('INSIGHTS_PASSWORD')
            response = requests.post(insights_upload,
                                     data={},
                                     files={'upload': ('payload.tar.gz',
                                                       upload_file,
                                                       'application/vnd.redhat.hccm.tar+tgz')},
                                     auth=(insights_user, insights_password),
                                     verify=False)
            if response.status_code == 202:
                print('File uploaded successfully.')
                print(response.text)
            else:
                print('{} File upload failed.'.format(response.status_code))
                print(response.text)


def _create_month_list(start_date, end_date):
    """Create a list of months given the date range args."""
    months = []
    current = start_date.replace(day=1)
    while current <= end_date:
        month = {}
        month['name'] = calendar.month_name[current.month]
        month['start'] = datetime(year=current.year, month=current.month, day=1)
        month['end'] = datetime(year=current.year,
                                month=current.month,
                                day=calendar.monthrange(year=current.year,
                                                        month=current.month)[1])
        if current.month == start_date.month:
            # First month start with start_date
            month['start'] = start_date
        if current.month == end_date.month:
            # Last month ends with end_date
            month['end'] = end_date

        months.append(month)
        current += relativedelta(months=+1)

    return months


def _aws_finalize_report(data):
    """Popualate invoice id for data."""
    data = copy.deepcopy(data)
    invoice_id = ''.join([random.choice(string.digits) for _ in range(9)])
    for row in data:
        row['bill/InvoiceId'] = invoice_id

    return data


def _generate_accounts(static_report_data=None):
    """Generate payer and useage accounts."""
    if static_report_data:
        payer_account = static_report_data.get('payer')
        usage_accounts = tuple(static_report_data.get('user'))
    else:
        fake = Faker()
        payer_account = fake.ean(length=13)  # pylint: disable=no-member
        usage_accounts = (payer_account,
                          fake.ean(length=13),  # pylint: disable=no-member
                          fake.ean(length=13),  # pylint: disable=no-member
                          fake.ean(length=13),  # pylint: disable=no-member
                          fake.ean(length=13))  # pylint: disable=no-member
    return payer_account, usage_accounts


def _get_generators(generator_list):
    """Collect a list of report generators."""
    generators = []
    if generator_list:
        for item in generator_list:
            for generator_cls, attributes in item.items():
                generator_obj = {}
                generator_obj['generator'] = getattr(importlib.import_module(__name__),
                                                     generator_cls)
                if attributes.get('start_date'):
                    attributes['start_date'] = parser.parse(attributes.get('start_date'))
                if attributes.get('end_date'):
                    attributes['end_date'] = parser.parse(attributes.get('end_date'))
                generator_obj['attributes'] = attributes
                generators.append(generator_obj)

    return generators


# pylint: disable=too-many-locals,too-many-statements
def aws_create_report(options):
    """Create a cost usage report file."""
    data = []
    start_date = options.get('start_date')
    end_date = options.get('end_date')
    aws_finalize_report = options.get('aws_finalize_report')

    static_report_data = options.get('static_report_data')
    if static_report_data:
        generators = _get_generators(static_report_data.get('generators'))
        accounts_list = static_report_data.get('accounts')
    else:
        generators = [{'generator': DataTransferGenerator, 'attributes': None},
                      {'generator': EBSGenerator, 'attributes': None},
                      {'generator': EC2Generator, 'attributes': None},
                      {'generator': S3Generator, 'attributes': None}]
        accounts_list = None

    months = _create_month_list(start_date, end_date)

    payer_account, usage_accounts = _generate_accounts(accounts_list)

    for month in months:
        data = []
        fake = Faker()
        for generator in generators:
            generator_cls = generator.get('generator')
            attributes = generator.get('attributes')
            gen_start_date = month.get('start')
            gen_end_date = month.get('end')
            if attributes:
                if attributes.get('start_date'):
                    gen_start_date = attributes.get('start_date')
                if attributes.get('end_date'):
                    gen_end_date = attributes.get('end_date')

            generator_end_date = gen_end_date + relativedelta(days=+1)
            gen = generator_cls(gen_start_date, generator_end_date, payer_account,
                                usage_accounts, attributes)
            data += gen.generate_data()

        month_output_file_name = '{}-{}-{}'.format(month.get('name'),
                                                   gen_start_date.year,
                                                   options.get('aws_report_name'))
        month_output_file = '{}/{}.csv'.format(os.getcwd(), month_output_file_name)
        if aws_finalize_report and aws_finalize_report == 'overwrite':
            data = _aws_finalize_report(data)
        elif aws_finalize_report and aws_finalize_report == 'copy':
            # Currently only a local option as this does not simulate
            finalized_data = _aws_finalize_report(data)
            finalized_file_name = '{}-finalized'.format(month_output_file_name)
            finalized_output_file = '{}/{}.csv'.format(
                os.getcwd(),
                finalized_file_name
            )
            _write_csv(finalized_output_file, finalized_data, AWS_COLUMNS)

        _write_csv(month_output_file, data, AWS_COLUMNS)

        aws_bucket_name = options.get('aws_bucket_name')
        if aws_bucket_name:
            report_name = options.get('aws_report_name')
            manifest_values = {'account': payer_account}
            manifest_values.update(options)
            manifest_values['start_date'] = gen_start_date
            manifest_values['end_date'] = gen_end_date
            s3_cur_path, manifest_data = aws_generate_manifest(fake, manifest_values)
            s3_assembly_path = os.path.dirname(s3_cur_path)
            s3_month_path = os.path.dirname(s3_assembly_path)
            s3_month_manifest_path = s3_month_path + '/' + report_name + '-Manifest.json'
            s3_assembly_manifest_path = s3_assembly_path + '/' + report_name + '-Manifest.json'
            temp_manifest = _write_manifest(manifest_data)
            temp_cur_zip = _gzip_report(month_output_file)
            aws_route_file(aws_bucket_name,
                           s3_month_manifest_path,
                           temp_manifest)
            aws_route_file(aws_bucket_name,
                           s3_assembly_manifest_path,
                           temp_manifest)
            aws_route_file(aws_bucket_name,
                           s3_cur_path,
                           temp_cur_zip)
            os.remove(temp_manifest)
            os.remove(temp_cur_zip)


def ocp_create_report(options):
    """Create a usage report file."""
    start_date = options.get('start_date')
    end_date = options.get('end_date')
    cluster_id = options.get('ocp_cluster_id')
    static_report_data = options.get('static_report_data')
    if static_report_data:
        generators = _get_generators(static_report_data.get('generators'))
    else:
        generators = [{'generator': OCPGenerator, 'attributes': None}]

    months = _create_month_list(start_date, end_date)
    for month in months:
        data = []
        for generator in generators:
            generator_cls = generator.get('generator')
            attributes = generator.get('attributes')
            gen_start_date = month.get('start')
            gen_end_date = month.get('end')
            if attributes:
                if attributes.get('start_date'):
                    gen_start_date = attributes.get('start_date')
                if attributes.get('end_date'):
                    gen_end_date = attributes.get('end_date')
            generator_end_date = gen_end_date + relativedelta(days=+1)
            gen = generator_cls(gen_start_date, generator_end_date, attributes)
            data += gen.generate_data()
        month_output_file_name = '{}-{}-{}'.format(month.get('name'),
                                                   gen_start_date.year,
                                                   cluster_id)
        month_output_file = '{}/{}.csv'.format(os.getcwd(), month_output_file_name)
        _write_csv(month_output_file, data, OCP_COLUMNS)

        insights_upload = options.get('insights_upload')
        if insights_upload:
            ocp_assembly_id = uuid4()
            report_datetime = gen_start_date
            manifest_values = {'ocp_cluster_id': cluster_id,
                               'ocp_assembly_id': ocp_assembly_id,
                               'report_datetime': report_datetime}
            manifest_data = ocp_generate_manifest(manifest_values)
            temp_manifest = _write_manifest(manifest_data)
            temp_filename = '{}_openshift_usage_report.csv'.format(ocp_assembly_id)
            temp_usage_file = create_temporary_copy(month_output_file, temp_filename, 'payload')
            temp_manifest = _write_manifest(manifest_data)
            temp_manifest_name = create_temporary_copy(temp_manifest, 'manifest.json', 'payload')
            temp_usage_zip = _tar_gzip_report(os.path.dirname(temp_manifest_name))
            ocp_route_file(insights_upload, temp_usage_zip)
            os.remove(temp_usage_file)
            os.remove(temp_manifest)
            os.remove(temp_manifest_name)
            os.remove(temp_usage_zip)

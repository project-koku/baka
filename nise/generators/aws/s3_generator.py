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
"""Module for s3 data generation."""
from random import choice, uniform

from nise.generators.aws.aws_generator import AWSGenerator


# pylint: disable=too-many-arguments
class S3Generator(AWSGenerator):
    """Generator for S3 data."""

    def __init__(self, start_date, end_date, payer_account, usage_accounts, attributes=None):
        """Initialize the S3 generator."""
        super().__init__(start_date, end_date, payer_account, usage_accounts, attributes)
        self._amount = uniform(0.2, 6000.99)
        self._rate = round(uniform(0.02, 0.06), 3)
        self._product_sku = self.fake.pystr(min_chars=12, max_chars=12).upper()  # pylint: disable=no-member
        self._attributes = None
        if attributes:
            self._attributes = attributes
            if attributes.get('amount'):
                self._amount = attributes.get('amount')
            if attributes.get('rate'):
                self._rate = attributes.get('rate')
            if attributes.get('product_sku'):
                self._product_sku = attributes.get('product_sku')
            if attributes.get('tags'):
                self._tags = attributes.get('tags')
    def _get_arn(self, avail_zone):
        """Create an amazon resource name."""
        arn = 'arn:aws:ec2:{}:{}:snapshot/snap-{}'.format(avail_zone,
                                                          self.payer_account,
                                                          self.fake.ean8())  # pylint: disable=no-member
        return arn

    def _pick_tag(self, tag_key, options):
        """Generate tag from options."""
        if self._tags:
            tags = self._tags.get(tag_key)
        elif self._attributes:
            tags = None
        else:
            tags = choice(options)
        return tags

    def _update_data(self, row, start, end, **kwargs):
        """Update data with generator specific data."""
        row = self._add_common_usage_info(row, start, end)

        rate = self._rate
        amount = self._amount
        cost = amount * rate
        location, aws_region, avail_zone, _ = self._get_location()
        description = '${} per GB-Month of snapshot data stored - {}'.format(rate, location)
        amazon_resource_name = self._get_arn(avail_zone)

        row['lineItem/ProductCode'] = 'AmazonS3'
        row['lineItem/UsageType'] = 'Requests-Tier2'
        row['lineItem/Operation'] = 'GetObject'
        row['lineItem/ResourceId'] = amazon_resource_name
        row['lineItem/UsageAmount'] = str(amount)
        row['lineItem/CurrencyCode'] = 'USD'
        row['lineItem/UnblendedRate'] = str(rate)
        row['lineItem/UnblendedCost'] = str(cost)
        row['lineItem/BlendedRate'] = str(rate)
        row['lineItem/BlendedCost'] = str(cost)
        row['lineItem/LineItemDescription'] = description
        row['product/ProductName'] = 'Amazon Simple Storage Service'
        row['product/location'] = location
        row['product/locationType'] = 'AWS Region'
        row['product/productFamily'] = 'Storage Snapshot'
        row['product/region'] = aws_region
        row['product/servicecode'] = 'AmazonS3'
        row['product/sku'] = self._product_sku
        row['product/storageMedia'] = 'Amazon S3'
        row['product/usagetype'] = 'Requests-Tier2'
        row['pricing/publicOnDemandCost'] = str(cost)
        row['pricing/publicOnDemandRate'] = str(rate)
        row['pricing/term'] = 'OnDemand'
        row['pricing/unit'] = 'GB-Mo'
        row['resourceTags/user:environment'] = self._pick_tag('resourceTags/user:environment',
                                                              ('dev', 'ci', 'qa', 'stage', 'prod'))
        row['resourceTags/user:version'] = self._pick_tag('resourceTags/user:version',
                                                          ('alpha', 'beta'))

        return row

    def generate_data(self):
        """Responsibile for generating data."""
        data = self._generate_hourly_data()
        return data

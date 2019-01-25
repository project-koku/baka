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
"""Defines the abstract generator."""
import datetime
from abc import abstractmethod
from random import choice, randint

from nise.generators.generator import AbstractGenerator


IDENTITY_COLS = ('identity/LineItemId', 'identity/TimeInterval')
BILL_COLS = ('bill/InvoiceId', 'bill/BillingEntity', 'bill/BillType',
             'bill/PayerAccountId', 'bill/BillingPeriodStartDate',
             'bill/BillingPeriodEndDate')
LINE_ITEM_COLS = ('lineItem/UsageAccountId',
                  'lineItem/LineItemType', 'lineItem/UsageStartDate',
                  'lineItem/UsageEndDate', 'lineItem/ProductCode',
                  'lineItem/UsageType', 'lineItem/Operation',
                  'lineItem/AvailabilityZone', 'lineItem/ResourceId',
                  'lineItem/UsageAmount', 'lineItem/NormalizationFactor',
                  'lineItem/NormalizedUsageAmount', 'lineItem/CurrencyCode',
                  'lineItem/UnblendedRate', 'lineItem/UnblendedCost',
                  'lineItem/BlendedRate', 'lineItem/BlendedCost',
                  'lineItem/LineItemDescription', 'lineItem/TaxType')
PRODUCT_COLS = ('product/ProductName', 'product/accountAssistance',
                'product/architecturalReview', 'product/architectureSupport',
                'product/availability', 'product/bestPractices',
                'product/caseSeverityresponseTimes', 'product/clockSpeed',
                'product/comments', 'product/contentType',
                'product/currentGeneration',
                'product/customerServiceAndCommunities',
                'product/databaseEngine', 'product/dedicatedEbsThroughput',
                'product/deploymentOption', 'product/description',
                'product/directorySize', 'product/directoryType',
                'product/directoryTypeDescription', 'product/durability',
                'product/ebsOptimized', 'product/ecu', 'product/endpointType',
                'product/engineCode', 'product/enhancedNetworkingSupported',
                'product/feeCode', 'product/feeDescription',
                'product/fromLocation', 'product/fromLocationType',
                'product/group', 'product/groupDescription',
                'product/includedServices', 'product/instanceFamily',
                'product/instanceType', 'product/isshadow',
                'product/iswebsocket', 'product/launchSupport',
                'product/licenseModel', 'product/location',
                'product/locationType', 'product/maxIopsBurstPerformance',
                'product/maxIopsvolume', 'product/maxThroughputvolume',
                'product/maxVolumeSize', 'product/memory', 'product/memoryGib',
                'product/messageDeliveryFrequency',
                'product/messageDeliveryOrder', 'product/minVolumeSize',
                'product/networkPerformance', 'product/operatingSystem',
                'product/operation', 'product/operationsSupport',
                'product/origin', 'product/physicalProcessor',
                'product/preInstalledSw', 'product/proactiveGuidance',
                'product/processorArchitecture', 'product/processorFeatures',
                'product/productFamily', 'product/programmaticCaseManagement',
                'product/protocol', 'product/provisioned', 'product/queueType',
                'product/recipient', 'product/region', 'product/requestDescription',
                'product/requestType', 'product/resourceEndpoint',
                'product/routingTarget', 'product/routingType',
                'product/servicecode', 'product/sku', 'product/softwareType',
                'product/storage', 'product/storageClass',
                'product/storageMedia', 'product/storageType',
                'product/technicalSupport', 'product/tenancy',
                'product/thirdpartySoftwareSupport', 'product/toLocation',
                'product/toLocationType', 'product/training',
                'product/transferType', 'product/usagetype', 'product/vcpu',
                'product/version', 'product/virtualInterfaceType',
                'product/volumeType', 'product/whoCanOpenCases')
PRICING_COLS = ('pricing/LeaseContractLength', 'pricing/OfferingClass'
                'pricing/PurchaseOption', 'pricing/publicOnDemandCost',
                'pricing/publicOnDemandRate', 'pricing/term', 'pricing/unit')
RESERVE_COLS = ('reservation/AvailabilityZone',
                'reservation/NormalizedUnitsPerReservation',
                'reservation/NumberOfReservations',
                'reservation/ReservationARN',
                'reservation/TotalReservedNormalizedUnits',
                'reservation/TotalReservedUnits',
                'reservation/UnitsPerReservation')
RESOURCE_TAG_COLS = ('resourceTags/user:environment',
                    'resourceTags/user:version')
AWS_COLUMNS = (IDENTITY_COLS + BILL_COLS + LINE_ITEM_COLS +  # noqa: W504
               PRODUCT_COLS + PRICING_COLS + RESERVE_COLS + RESOURCE_TAG_COLS)


# pylint: disable=too-few-public-methods
class AWSGenerator(AbstractGenerator):
    """Defines a abstract class for generators."""

    REGIONS = (
        ('US East (N. Virginia)', 'us-east-1', 'us-east-1a', 'USE1-EBS'),
        ('US East (N. Virginia)', 'us-east-1', 'us-east-1b', 'USE1-EBS'),
        ('US West (N. California)', 'us-west-1', 'us-west-1a', 'USW1-EBS'),
        ('US West (N. California)', 'us-west-1', 'us-west-1b', 'USW1-EBS'),
        ('US West (Oregon)', 'us-west-2', 'us-west-2a', 'USW2-EBS'),
        ('US West (Oregon)', 'us-west-2', 'us-west-2b', 'USW2-EBS'),
    )

    def __init__(self, start_date, end_date, payer_account, usage_accounts, attributes):
        """Initialize the generator."""
        self.payer_account = payer_account
        self.usage_accounts = usage_accounts
        self.attributes = attributes
        self.num_instances = 1 if attributes else randint(2, 60)
        super().__init__(start_date, end_date)

    @staticmethod
    def timestamp(in_date):
        """Provide timestamp for a date."""
        if not in_date or not isinstance(in_date, datetime.datetime):
            raise ValueError('in_date must be a date object.')
        return in_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def time_interval(start, end):
        """Create a time interval string from input dates."""
        start_str = AWSGenerator.timestamp(start)
        end_str = AWSGenerator.timestamp(end)
        time_interval = str(start_str) + '/' + str(end_str)
        return time_interval

    def _init_data_row(self, start, end):  # noqa: C901
        """Create a row of data with placeholder for all headers."""
        if not start or not end:
            raise ValueError('start and end must be date objects.')
        if not isinstance(start, datetime.datetime):
            raise ValueError('start must be a date object.')
        if not isinstance(end, datetime.datetime):
            raise ValueError('end must be a date object.')

        bill_begin = start.replace(microsecond=0, second=0, minute=0, hour=0, day=1)
        bill_end = AbstractGenerator.next_month(bill_begin)
        row = {}
        for column in AWS_COLUMNS:
            row[column] = ''
            if column == 'identity/LineItemId':
                # pylint: disable=no-member
                row[column] = self.fake.sha1(raw_output=False)
            elif column == 'identity/TimeInterval':
                row[column] = AWSGenerator.time_interval(start, end)
            elif column == 'bill/BillingEntity':
                row[column] = 'AWS'
            elif column == 'bill/BillType':
                row[column] = 'Anniversary'
            elif column == 'bill/PayerAccountId':
                row[column] = self.payer_account
            elif column == 'bill/BillingPeriodStartDate':
                row[column] = AWSGenerator.timestamp(bill_begin)
            elif column == 'bill/BillingPeriodEndDate':
                row[column] = AWSGenerator.timestamp(bill_end)
        return row

    def _get_location(self):
        """Pick instance location."""
        if self.attributes:
            # TODO: Make region configurable. 
            return ('US East (N. Virginia)', 'us-east-1', 'us-east-1a', 'USE1-EBS')
        else:
            return choice(self.REGIONS)

    def _add_common_usage_info(self, row, start, end):
        """Add common usage information."""
        row['lineItem/UsageAccountId'] = choice(self.usage_accounts)
        row['lineItem/LineItemType'] = 'Usage'
        row['lineItem/UsageStartDate'] = start
        row['lineItem/UsageEndDate'] = end
        return row

    @abstractmethod
    def _update_data(self, row, start, end, **kwargs):
        """Update data with generator specific data."""

    def _generate_hourly_data(self):
        """Create houldy data."""
        data = []
        for hour in self.hours:
            start = hour.get('start')
            end = hour.get('end')
            row = self._init_data_row(start, end)
            row = self._update_data(row, start, end)
            data.append(row)
        return data

    @abstractmethod
    def generate_data(self):
        """Responsibile for generating data."""

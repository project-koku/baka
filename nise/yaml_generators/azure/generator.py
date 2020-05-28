#
# Copyright 2020 Red Hat, Inc.
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
"""Utility to generate koku-nise Azure yaml files"""
import logging
import os
import random
from calendar import monthrange
from datetime import date

import faker
from dateutil.relativedelta import relativedelta
from nise.yaml_generators.generator import Generator
from nise.yaml_generators.utils import dicta
from nise.yaml_generators.utils import generate_name
from nise.yaml_generators.utils import generate_resource_id

# from uuid import uuid4

FAKER = faker.Faker()
LOG = logging.getLogger(__name__)
TAG_KEYS = {
    "vmachine": ["environment", "version", "app"],
    "vnetwork": ["environment", "version", "app"],
    "storage": ["environment", "version", "app", "storageclass"],
    "sql": ["environment", "version", "app"],
    "bandwidth": ["environment", "version", "app"],
}


def generate_tags(key, config, prefix="", suffix="", dynamic=True):
    """Generate properly formatted AWS tags.
    Returns:
        list
    """
    key_list = TAG_KEYS.get(key)
    keys = random.sample(key_list, k=random.randint(1, len(key_list)))
    return [dicta(key=key, v=generate_name(config)) for key in keys]


class AzureGenerator(Generator):
    """YAML generator for Azure."""

    def init_config(self, args):
        """Process provider specific args."""
        config = super().init_config(args)

        # insert specific config variables

        return config

    def build_data(self, config, _random=False):  # noqa: C901
        """

        """
        LOG.info("Data build starting")

        data = dicta(bandwidth_gens=[], sql_gens=[], storage_gens=[], vmachine_gens=[], vnetwork_gens=[])

        max_bandwidth_gens = FAKER.random_int(1, config.max_bandwidth_gens) if _random else config.max_bandwidth_gens
        max_sql_gens = FAKER.random_int(1, config.max_sql_gens) if _random else config.max_sql_gens
        max_storage_gens = FAKER.random_int(1, config.max_storage_gens) if _random else config.max_storage_gens
        max_vmachine_gens = FAKER.random_int(1, config.max_vmachine_gens) if _random else config.max_vmachine_gens
        max_vnetwork_gens = FAKER.random_int(1, config.max_vnetwork_gens) if _random else config.max_vnetwork_gens

        LOG.info(f"Building {max_bandwidth_gens} Bandwidth generators ...")
        for _ in range(max_bandwidth_gens):
            bandwidth_gen = dicta(
                start_date=str(config.start_date),
                end_date=str(config.end_date),
                resource_id=generate_resource_id(config),
                tags=generate_tags("bandwidth", config),
            )
            data.bandwidth_gens.append(bandwidth_gen)

        LOG.info(f"Building {max_sql_gens} SQL generators ...")
        for _ in range(max_sql_gens):
            sql_gen = dicta(
                start_date=str(config.start_date), end_date=str(config.end_date), tags=generate_tags("sql", config)
            )
            data.sql_gens.append(sql_gen)

        LOG.info(f"Building {max_storage_gens} Storage generators ...")
        for _ in range(max_storage_gens):

            storage_gen = dicta(
                start_date=str(config.start_date),
                end_date=str(config.end_date),
                resource_id=generate_resource_id(config),
                tags=generate_tags("storage", config),
            )
            data.storage_gens.append(storage_gen)

        LOG.info(f"Building {max_vmachine_gens} Virtual Machine generators ...")
        for _ in range(max_vmachine_gens):

            vmachine_gen = dicta(
                start_date=str(config.start_date),
                end_date=str(config.end_date),
                resource_id=generate_resource_id(config),
                tags=generate_tags("vmachine", config),
            )

            data.vmachine_gens.append(vmachine_gen)

        LOG.info(f"Building {max_vnetwork_gens} Virtual Network generators ...")
        for _ in range(max_vnetwork_gens):

            vnetwork_gen = dicta(
                start_date=str(config.start_date),
                end_date=str(config.end_date),
                resource_id=generate_resource_id(config),
                tags=generate_tags("vnetwork", config),
            )

            data.vnetwork_gens.append(vnetwork_gen)

        LOG.info(data)

        return data

    def default_config(self):
        """
        Generate a config object with all values set to defaults
        Returns:
            dicta
        """
        default_date = date.today()
        last_day_of_month = monthrange(default_date.year, default_date.month)[1]
        return dicta(
            start_date=default_date.replace(day=1) - relativedelta(months=1),
            end_date=default_date.replace(day=last_day_of_month),
            max_name_words=2,
            max_resource_id_length=10,
            max_bandwidth_gens=1,
            max_sql_db_gens=1,
            max_storage_gens=1,
            max_vmachine_gens=1,
            max_vnetwork_gens=1,
        )

    def validate_config(self, config):
        """
        Validates that all known parts of a config are the required types
        Params:
            config : dicta - the configuration to test
        Returns:
            bool
        """
        validator = dicta(
            start_date=date,
            end_date=date,
            storage_classes=list,
            max_name_words=int,
            max_resource_id_length=int,
            max_bandwidth_gens=int,
            max_sql_db_gens=int,
            max_storage_gens=int,
            max_vmachine_gens=int,
            max_vnetwork_gens=int,
        )
        result = [
            f"{k} Must be of type {validator[k].__name__}"
            for k in validator
            if k in config and not isinstance(config[k], validator[k])
        ]
        if result:
            raise TypeError(os.linesep.join(result))

        return True

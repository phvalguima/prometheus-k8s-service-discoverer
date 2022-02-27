#!/usr/bin/env python3
# Copyright 2022 pguimaraes
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

import yaml
import logging

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus
from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider, _sanitize_scrape_configuration

logger = logging.getLogger(__name__)


class PrometheusK8SServiceDiscovererCharm(CharmBase):
    """Charm the service."""

    def _generate_metrics_provider_job(self):
        relabel_configs = yaml.safe_load(self.config["relabel_configs"])
        return [
                {
                    "job_name": "k8s_sd_charm",
                    "scrape_interval": self.config["scrape_interval"],
                    "kubernetes_sd_configs": self.config["kubernetes_sd_configs"],
                    "relabel_configs": relabel_configs,
                }
            ]

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.config_changed, self.on_config_changed)
        ops_events = [
            self.on["monitoring"].relation_changed,
            self.on["monitoring"].relation_broken,
            self.on["monitoring"].relation_departed,
        ]
        for e in ops_events:
            self.framework.observe(e, self.on_config_changed)
        if self.unit.is_leader():
            self.prometheus_provider = MetricsEndpointProvider(
                charm=self,
                relation_name="monitoring",
                jobs=self._generate_metrics_provider_job(),
            )
        else:
            self.prometheus_provider = None

    def on_config_changed(self, event):
        """Configures the service discoverer following the
        options set by the operator.
        """
        if not self.unit.is_leader():
            return
        # If it is a fresh new leader, self.prometheus_provider will
        # not be set yet
        if not self.prometheus_provider:
            self.prometheus_provider = MetricsEndpointProvider(
                charm=self,
                relation_name="monitoring",
                jobs=self._generate_metrics_provider_job(),
            )
            return
        # Otherwise, update "self._jobs" in the relation:
        self.prometheus_provider._jobs = [_sanitize_scrape_configuration(job) for job in self._generate_metrics_provider_job()]

if __name__ == "__main__":
    main(PrometheusK8SServiceDiscovererCharm)

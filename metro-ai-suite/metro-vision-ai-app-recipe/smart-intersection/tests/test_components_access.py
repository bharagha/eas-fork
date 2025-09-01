# SPDX-FileCopyrightText: (C) 2025 Intel Corporation
# SPDX-License-Identifier: LicenseRef-Intel-Edge-Software
# This file is licensed under the Limited Edge Software Distribution License Agreement.

import pytest
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from tests.utils.ui_utils import waiter, driver
from tests.utils.utils import check_urls_access
from .conftest import (
  SCENESCAPE_URL,  
  SCENESCAPE_REMOTE_URL,
  GRAFANA_URL,
  GRAFANA_REMOTE_URL,
  INFLUX_DB_URL,
  INFLUX_REMOTE_DB_URL,
  NODE_RED_URL,
  NODE_RED_REMOTE_URL,
  INFLUX_DB_ADMIN_USERNAME,
  INFLUX_DB_ADMIN_PASSWORD,
  get_scenescape_kubernetes_url,
)

def components_access_functionality_check(scenescape_url):
  """
  Helper function to test that all application components are accessible.

  Args:
    scenescape_url: The scenescape URL to test (either Kubernetes or Docker)
  """
  urls_to_check = [
    scenescape_url,
    GRAFANA_URL,
    INFLUX_DB_URL,
    NODE_RED_URL,
  ]

  check_urls_access(urls_to_check)

def remote_components_access_functionality_check(scenescape_remote_url, grafana_remote_url, influx_remote_url, nodered_remote_url):
  """
  Helper function to test that all remote application components are accessible.
  Skips the test if any of the remote URL environment variables are not set.

  Args:
    scenescape_remote_url: Remote Scenescape URL to test
    grafana_remote_url: Remote Grafana URL to test
    influx_remote_url: Remote InfluxDB URL to test
    nodered_remote_url: Remote Node-RED URL to test
  """
  urls_to_check = [
    scenescape_remote_url,
    grafana_remote_url,
    influx_remote_url,
    nodered_remote_url
  ]

  # Check if any URL is not set
  if any(url is None or url == "" for url in urls_to_check):
    pytest.skip("One or more remote URL environment variables are not set")

  check_urls_access(urls_to_check)

@pytest.mark.kubernetes
@pytest.mark.zephyr_id("NEX-T10677")
def test_components_access_kubernetes():
  """Test that all application components are accessible."""
  components_access_functionality_check(get_scenescape_kubernetes_url())

@pytest.mark.docker
@pytest.mark.zephyr_id("NEX-T9368")
def test_components_access_docker():
  """Test that all application components are accessible."""
  components_access_functionality_check(SCENESCAPE_URL)

@pytest.mark.kubernetes
@pytest.mark.zephyr_id("NEX-T10678")
def test_remote_components_access_kubernetes():
  """Test that all remote application components are accessible."""
  remote_components_access_functionality_check(
    SCENESCAPE_REMOTE_URL,
    GRAFANA_REMOTE_URL,
    INFLUX_REMOTE_DB_URL,
    NODE_RED_REMOTE_URL
  )

@pytest.mark.docker
@pytest.mark.zephyr_id("NEX-T9369")
def test_remote_components_access_docker():
  """Test that all remote application components are accessible."""
  remote_components_access_functionality_check(
    SCENESCAPE_REMOTE_URL,
    GRAFANA_REMOTE_URL,
    INFLUX_REMOTE_DB_URL,
    NODE_RED_REMOTE_URL
  )

@pytest.mark.docker
@pytest.mark.zephyr_id("NEX-T9623")
def test_grafana_failed_login_docker(waiter):
  waiter.perform_login(
    GRAFANA_URL,
    By.CSS_SELECTOR, "[data-testid='data-testid Username input field']",
    By.CSS_SELECTOR, "[data-testid='data-testid Password input field']",
    By.CSS_SELECTOR, "[data-testid='data-testid Login button']",
    "wrong_username", "wrong_password"
  )

  # Wait for the error message element to appear
  waiter.wait_and_assert(
    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='data-testid Alert error']")),
    error_message="Login error message not found within 10 seconds"
  )

@pytest.mark.docker
@pytest.mark.zephyr_id("NEX-T9617")
def test_influx_db_login_docker(waiter):
  waiter.perform_login(
    INFLUX_DB_URL,
    By.CSS_SELECTOR, "[data-testid='username']",
    By.CSS_SELECTOR, "[data-testid='password']",
    By.CSS_SELECTOR, "[data-testid='button']",
    INFLUX_DB_ADMIN_USERNAME, INFLUX_DB_ADMIN_PASSWORD
  )

  # Wait for the header element to be visible after login
  waiter.wait_and_assert(
    EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='home-page--header']")),
    error_message='Welcome message not visible within 10 seconds after login'
  )

@pytest.mark.docker
@pytest.mark.zephyr_id("NEX-T9619")
def test_remote_influx_db_login_docker(waiter):
  if not INFLUX_REMOTE_DB_URL:
    pytest.skip("INFLUX_REMOTE_DB_URL is not set")

  waiter.perform_login(
    INFLUX_REMOTE_DB_URL,
    By.CSS_SELECTOR, "[data-testid='username']",
    By.CSS_SELECTOR, "[data-testid='password']",
    By.CSS_SELECTOR, "[data-testid='button']",
    INFLUX_DB_ADMIN_USERNAME, INFLUX_DB_ADMIN_PASSWORD
  )

  # Wait for the header element to be visible after login
  waiter.wait_and_assert(
    EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='home-page--header']")),
    error_message='Welcome message not visible within 10 seconds after login'
  )

@pytest.mark.docker
@pytest.mark.zephyr_id("NEX-T9621")
def test_influx_db_failed_login_docker(waiter):
  waiter.perform_login(
    INFLUX_DB_URL,
    By.CSS_SELECTOR, "[data-testid='username']",
    By.CSS_SELECTOR, "[data-testid='password']",
    By.CSS_SELECTOR, "[data-testid='button']",
    "wrong_username", "wrong_password"
  )

  # Wait for the error notification to be visible after failed login
  waiter.wait_and_assert(
    EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='notification-error--children']")),
    error_message='Error notification not visible within 10 seconds after failed login'
  )

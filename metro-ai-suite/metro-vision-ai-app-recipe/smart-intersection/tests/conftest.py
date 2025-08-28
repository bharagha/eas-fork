# SPDX-FileCopyrightText: (C) 2025 Intel Corporation
# SPDX-License-Identifier: LicenseRef-Intel-Edge-Software
# This file is licensed under the Limited Edge Software Distribution License Agreement.

import pytest
import logging
import time
import os
import subprocess
import requests
import urllib.parse
from dotenv import load_dotenv
from tests.utils.utils import (
  run_command,
  check_url_access,
  get_node_port,
  get_password_from_supass_file,
  get_username_from_influxdb2_admin_username_file,
  get_password_from_influxdb2_admin_password_file
)

load_dotenv()
logger = logging.getLogger(__name__)

SCENESCAPE_URL = os.getenv("SCENESCAPE_URL", "https://localhost")
SCENESCAPE_REMOTE_URL = os.getenv("SCENESCAPE_REMOTE_URL")

SCENESCAPE_USERNAME = os.getenv("SCENESCAPE_USERNAME", "admin")
SCENESCAPE_PASSWORD = os.getenv("SCENESCAPE_PASSWORD", get_password_from_supass_file())

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_REMOTE_URL = os.getenv("GRAFANA_REMOTE_URL")
GRAFANA_USERNAME = os.getenv("GRAFANA_USERNAME", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "admin")

INFLUX_DB_URL = os.getenv("INFLUX_DB_URL", "http://localhost:8086")
INFLUX_REMOTE_DB_URL = os.getenv("INFLUX_REMOTE_DB_URL")
INFLUX_DB_ADMIN_USERNAME = os.getenv("INFLUX_DB_ADMIN_USERNAME", get_username_from_influxdb2_admin_username_file())
INFLUX_DB_ADMIN_PASSWORD = os.getenv("INFLUX_DB_ADMIN_PASSWORD", get_password_from_influxdb2_admin_password_file())

NODE_RED_URL = os.getenv("NODE_RED_URL", "http://localhost:1880")
NODE_RED_REMOTE_URL = os.getenv("NODE_RED_REMOTE_URL")

PROJECT_GITHUB_URL = os.getenv("PROJECT_GITHUB_URL", "https://github.com/open-edge-platform/edge-ai-suites/blob/main/metro-ai-suite/smart-intersection")

# This will be set dynamically during Kubernetes setup
SCENESCAPE_KUBERNETES_URL = None

def get_scenescape_kubernetes_url():
  """Get the Kubernetes URL for Scenescape service."""
  if SCENESCAPE_KUBERNETES_URL is None:
    web_node_port = get_node_port("smart-intersection-web", "smart-intersection")
    return f"{SCENESCAPE_URL}:{web_node_port}"
  return SCENESCAPE_KUBERNETES_URL

def get_pod_name(service_name, namespace="smart-intersection"):
  """Get the name of the first pod for a given service."""
  cmd = f"kubectl get pods -n {namespace} -l app={service_name} -o jsonpath='{{.items[0].metadata.name}}'"
  return subprocess.check_output(cmd, shell=True).decode().strip()

def start_port_forwarding(service_name, local_port, remote_port, namespace="smart-intersection"):
  """Start port forwarding for a service and return the process."""
  pod_name = get_pod_name(service_name, namespace)
  cmd = f"kubectl -n {namespace} port-forward {pod_name} {local_port}:{remote_port}"
  logger.info(f"Starting port forwarding for {service_name}: localhost:{local_port}")
  return subprocess.Popen(cmd, shell=True)

def start_remote_port_forwarding(service_name, remote_host, local_port, remote_port, namespace="smart-intersection"):
  """Start remote port forwarding for a service and return the process."""
  pod_name = get_pod_name(service_name, namespace)
  
  # Use sudo with password for privileged ports (<1024)
  if local_port < 1024:
    sudo_password = os.environ.get('SUDO_PASSWORD')
    if not sudo_password:
      logger.error("SUDO_PASSWORD not set in environment variables, but required for privileged port")
      raise ValueError("SUDO_PASSWORD environment variable is required for ports < 1024. Set it with: export SUDO_PASSWORD=\"your_password\"")
    
    # Use echo to pipe password to sudo -S (stdin) and preserve environment with -E
    cmd = f'echo "{sudo_password}" | sudo -S -E kubectl -n {namespace} port-forward {pod_name} {local_port}:{remote_port} --address {remote_host}'
  else:
    cmd = f"kubectl -n {namespace} port-forward {pod_name} {local_port}:{remote_port} --address {remote_host}"
    
  logger.info(f"Starting remote port forwarding for {service_name}: {remote_host}:{local_port}")
  return subprocess.Popen(cmd, shell=True)

def stop_port_forwarding_process(process_name, process):
  """Safely stop a port forwarding process."""
  if process and process.poll() is None:  # Check if process is still running
    try:
      logger.info(f"Terminating {process_name} port forwarding...")
      process.terminate()
      process.wait(timeout=5)  # Wait up to 5 seconds for clean termination
    except subprocess.TimeoutExpired:
      logger.warning(f"Force killing {process_name} port forwarding...")
      process.kill()
    except Exception as e:
      logger.error(f"Error stopping {process_name} port forwarding: {e}")

def are_remote_urls_configured():
  """Check if any remote URLs are configured in the environment."""
  return any([
    SCENESCAPE_REMOTE_URL,
    GRAFANA_REMOTE_URL,
    INFLUX_REMOTE_DB_URL,
    NODE_RED_REMOTE_URL
  ])

def wait_for_services_readiness(services_urls, timeout=120, interval=2):
  """
  Waits for services to become available.

  :param services_urls: List of URLs to check.
  :param timeout: Maximum time to wait for services to be available (in seconds).
  :param interval: Time between checks (in seconds).
  :raises TimeoutError: If services are not available within the timeout period.
  """
  start_time = time.time()
  while time.time() - start_time < timeout:
    all_services_ready = True
    for url in services_urls:
      try:
        check_url_access(url)
      except AssertionError as e:
        all_services_ready = False
        break
    if all_services_ready:
      logger.info("All services are ready.")
      return True
    logger.info("Waiting for services to be ready...")
    time.sleep(interval)
  raise TimeoutError("Services did not become ready in time.")

def wait_for_pods_ready(namespace, timeout=300, interval=10):
  """Wait for all pods in the specified namespace to be in 'Running' state."""
  start_time = time.time()
  while time.time() - start_time < timeout:
    out, err, code = run_command(f"kubectl get pods -n {namespace} --no-headers")
    if code != 0:
      logger.error(f"Failed to get pods: {err}")
      raise RuntimeError("Failed to get pods status")

    pods = out.strip().split("\n")
    all_running = all("Running" in pod for pod in pods)
    if all_running:
      logger.info("All pods are in 'Running' state.")
      return True

    logger.info("Waiting for pods to be ready...")
    time.sleep(interval)

  raise TimeoutError("Pods did not become ready in time.")

@pytest.fixture(scope="session", autouse=True)
def setup_environment(request):
  """Set up Docker or Kubernetes environment for testing."""
  
  # Clean up any existing port forwarding processes from previous runs
  logger.info("Cleaning up any existing port forwarding processes...")
  run_command("pkill -f 'kubectl.*port-forward' || true")
  
  # Initialize port forwarding process variables  
  web_port_forward_process = None
  grafana_port_forward_process = None
  influxdb_port_forward_process = None
  nodered_port_forward_process = None
  
  # Remote port forwarding process variables
  remote_web_port_forward_process = None
  remote_grafana_port_forward_process = None
  remote_influxdb_port_forward_process = None
  remote_nodered_port_forward_process = None
  
  try:
    if "kubernetes" in request.config.getoption("markexpr"):
      logger.info("Deploying Kubernetes environment...")
      out, err, code = run_command(
        "helm upgrade --install smart-intersection ./chart "
        "--create-namespace "
        "--set grafana.service.type=NodePort "
        "-n smart-intersection"
      )
      assert code == 0, f"Kubernetes deployment failed: {err}"
      logger.info("Kubernetes environment deployed.")

      # Wait for all pods to be ready
      wait_for_pods_ready("smart-intersection")
      
      # Get dynamic NodePort
      web_node_port = get_node_port("smart-intersection-web", "smart-intersection")
      
      # Set global SCENESCAPE_KUBERNETES_URL
      global SCENESCAPE_KUBERNETES_URL
      SCENESCAPE_KUBERNETES_URL = f"{SCENESCAPE_URL}:{web_node_port}"
      logger.info(f"SCENESCAPE_KUBERNETES_URL set to: {SCENESCAPE_KUBERNETES_URL}")

      # Start port forwarding for localhost access only
      web_port_forward_process = start_port_forwarding("smart-intersection-web", web_node_port, 443)
      grafana_port_forward_process = start_port_forwarding("smart-intersection-grafana", 3000, 3000)
      influxdb_port_forward_process = start_port_forwarding("smart-intersection-influxdb", 8086, 8086)
      nodered_port_forward_process = start_port_forwarding("smart-intersection-nodered", 1880, 1880)

      # Check localhost service readiness
      localhost_services_urls = [
        SCENESCAPE_KUBERNETES_URL,
        GRAFANA_URL,
        INFLUX_DB_URL,
        NODE_RED_URL
      ]
      wait_for_services_readiness(localhost_services_urls)
      
      # Check remote service readiness only if remote URLs are configured
      if are_remote_urls_configured():        
        # Start remote port forwarding for each configured service
        if SCENESCAPE_REMOTE_URL:
          parsed = urllib.parse.urlparse(SCENESCAPE_REMOTE_URL)
          logger.info(f"SCENESCAPE_REMOTE_URL: {SCENESCAPE_REMOTE_URL}")
          logger.info(f"parsed.hostname: {parsed.hostname}, parsed.port: {parsed.port}")
          remote_web_port_forward_process = start_remote_port_forwarding("smart-intersection-web", parsed.hostname, 443, 443)
          
        if GRAFANA_REMOTE_URL:
          parsed = urllib.parse.urlparse(GRAFANA_REMOTE_URL)
          logger.info(f"GRAFANA_REMOTE_URL: {GRAFANA_REMOTE_URL}")
          logger.info(f"parsed.hostname: {parsed.hostname}, parsed.port: {parsed.port}")
          remote_grafana_port_forward_process = start_remote_port_forwarding("smart-intersection-grafana", parsed.hostname, parsed.port, 3000)
          
        if INFLUX_REMOTE_DB_URL:
          parsed = urllib.parse.urlparse(INFLUX_REMOTE_DB_URL)
          logger.info(f"INFLUX_REMOTE_DB_URL: {INFLUX_REMOTE_DB_URL}")
          logger.info(f"parsed.hostname: {parsed.hostname}, parsed.port: {parsed.port}")
          remote_influxdb_port_forward_process = start_remote_port_forwarding("smart-intersection-influxdb", parsed.hostname, parsed.port, 8086)
          
        if NODE_RED_REMOTE_URL:
          parsed = urllib.parse.urlparse(NODE_RED_REMOTE_URL)
          logger.info(f"NODE_RED_REMOTE_URL: {NODE_RED_REMOTE_URL}")
          logger.info(f"parsed.hostname: {parsed.hostname}, parsed.port: {parsed.port}")
          remote_nodered_port_forward_process = start_remote_port_forwarding("smart-intersection-nodered", parsed.hostname, parsed.port, 1880)
        
        # Build list of remote URLs to check
        remote_services_urls = []
        if SCENESCAPE_REMOTE_URL:
          logger.info(f"Adding SCENESCAPE_REMOTE_URL: {SCENESCAPE_REMOTE_URL}")
          remote_services_urls.append(SCENESCAPE_REMOTE_URL)
        if GRAFANA_REMOTE_URL:
          logger.info(f"Adding GRAFANA_REMOTE_URL: {GRAFANA_REMOTE_URL}")
          remote_services_urls.append(GRAFANA_REMOTE_URL)
        if INFLUX_REMOTE_DB_URL:
          logger.info(f"Adding INFLUX_REMOTE_DB_URL: {INFLUX_REMOTE_DB_URL}")
          remote_services_urls.append(INFLUX_REMOTE_DB_URL)
        if NODE_RED_REMOTE_URL:
          logger.info(f"Adding NODE_RED_REMOTE_URL: {NODE_RED_REMOTE_URL}")
          remote_services_urls.append(NODE_RED_REMOTE_URL)
        
        if remote_services_urls:
          logger.info(f"Checking {len(remote_services_urls)} remote services: {remote_services_urls}")
          wait_for_services_readiness(remote_services_urls)
          logger.info("All remote services are ready.")
        else:
          logger.info("No valid remote URLs found.")
      else:
        logger.info("No remote URLs configured, skipping remote services check.")

    else:
      logger.info("Building and deploying Docker containers...")
      out, err, code = run_command("docker compose up -d")
      assert code == 0, f"Build and Deploy failed: {err}"
      logger.info("Docker containers deployed.")

      # Check localhost service readiness for Docker
      localhost_services_urls = [SCENESCAPE_URL, GRAFANA_URL, INFLUX_DB_URL, NODE_RED_URL]
      logger.info(f"Checking {len(localhost_services_urls)} localhost services: {localhost_services_urls}")
      wait_for_services_readiness(localhost_services_urls)
      
      # Check remote service readiness only if remote URLs are configured
      if are_remote_urls_configured():
        logger.info("Remote URLs are configured, checking remote services readiness...")
        remote_services_urls = []
        if SCENESCAPE_REMOTE_URL:
          logger.info(f"Adding SCENESCAPE_REMOTE_URL: {SCENESCAPE_REMOTE_URL}")
          remote_services_urls.append(SCENESCAPE_REMOTE_URL)
        if GRAFANA_REMOTE_URL:
          logger.info(f"Adding GRAFANA_REMOTE_URL: {GRAFANA_REMOTE_URL}")
          remote_services_urls.append(GRAFANA_REMOTE_URL)
        if INFLUX_REMOTE_DB_URL:
          logger.info(f"Adding INFLUX_REMOTE_DB_URL: {INFLUX_REMOTE_DB_URL}")
          remote_services_urls.append(INFLUX_REMOTE_DB_URL)
        if NODE_RED_REMOTE_URL:
          logger.info(f"Adding NODE_RED_REMOTE_URL: {NODE_RED_REMOTE_URL}")
          remote_services_urls.append(NODE_RED_REMOTE_URL)
        
        if remote_services_urls:
          logger.info(f"Checking {len(remote_services_urls)} remote services: {remote_services_urls}")
          wait_for_services_readiness(remote_services_urls)
          logger.info("All remote services are ready.")
        else:
          logger.info("No valid remote URLs found.")
      else:
        logger.info("No remote URLs configured, skipping remote services check.")

    yield
    
  finally:
    # Cleanup - this ALWAYS runs regardless of success/failure
    if "kubernetes" in request.config.getoption("markexpr"):
      logger.info("Tearing down Kubernetes environment...")
      
      # Stop port forwarding processes first
      for process_name, process in [
        ("web", web_port_forward_process),
        ("grafana", grafana_port_forward_process), 
        ("influxdb", influxdb_port_forward_process),
        ("nodered", nodered_port_forward_process),
        ("remote-web", remote_web_port_forward_process),
        ("remote-grafana", remote_grafana_port_forward_process),
        ("remote-influxdb", remote_influxdb_port_forward_process),
        ("remote-nodered", remote_nodered_port_forward_process)
      ]:
        stop_port_forwarding_process(process_name, process)
      
      logger.info("Port forwarding stopped.")
      
      # Clean up Kubernetes resources  
      run_command("helm uninstall smart-intersection -n smart-intersection")
      run_command("kubectl delete namespace smart-intersection")
      logger.info("Kubernetes environment removed.")
    else:
      logger.info("Tearing down Docker containers...")
      run_command("docker compose down")
      logger.info("Docker containers stopped and removed.")

      logger.info("Removing Docker volumes...")
      run_command("docker volume ls | grep metro-vision-ai-app-recipe | awk '{ print $2 }' | xargs docker volume rm")
      logger.info("Docker volumes removed.")
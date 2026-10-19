"""
Locust load testing suite for GrowCircle platform.
Simulates high-concurrency traffic across Mandi Price queries, Geodesic distance lookups,
IVR missed calls, WhatsApp webhooks, and Consumer Seasonality checks.
"""

from locust import HttpUser, between, task


class GrowCircleUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(5)
    def check_today_prices(self) -> None:
        """Simulate household and farmer checking modal rates."""
        self.client.get(
            "/prices?crop=banana&state=andhra-pradesh&district=guntur",
            name="/prices [banana guntur]",
        )

    @task(3)
    def check_nearby_mandis(self) -> None:
        """Simulate PostGIS geospatial nearest mandi lookup."""
        self.client.get(
            "/nearby-mandis?lat=16.3067&lng=80.4365&crop=banana&limit=3",
            name="/nearby-mandis [postgis radius]",
        )

    @task(3)
    def check_seasonality(self) -> None:
        """Simulate consumer asking 'is it expensive this month?'."""
        self.client.get(
            "/consumer/seasonality/banana?district=Guntur",
            name="/consumer/seasonality",
        )

    @task(2)
    def health_check(self) -> None:
        """Simulate load balancer synthetic health probe."""
        self.client.get("/health", name="/health")

    @task(1)
    def scrape_metrics(self) -> None:
        """Simulate Prometheus scraper."""
        self.client.get("/metrics", name="/metrics")

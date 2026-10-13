"""
Unit tests for geospatial distance calculations and nearest mandi logic.
"""

from backend.app.services.geo import haversine_distance_km


def test_haversine_distance_known_coordinates() -> None:
    # Guntur (16.3067, 80.4365) to Vijayawada (16.5062, 80.6480)
    guntur_lat, guntur_lng = 16.3067, 80.4365
    vja_lat, vja_lng = 16.5062, 80.6480

    dist_vja = haversine_distance_km(guntur_lat, guntur_lng, vja_lat, vja_lng)
    # Physical road distance ~35km, geodesic distance ~31.1 km
    assert 28.0 <= dist_vja <= 35.0

    # Guntur to Madanapalle (13.5500, 78.5000)
    mad_lat, mad_lng = 13.5500, 78.5000
    dist_mad = haversine_distance_km(guntur_lat, guntur_lng, mad_lat, mad_lng)
    assert 350.0 <= dist_mad <= 420.0

    # Closer mandi must have smaller distance
    assert dist_vja < dist_mad


def test_zero_distance_same_point() -> None:
    dist = haversine_distance_km(16.3067, 80.4365, 16.3067, 80.4365)
    assert dist == 0.0

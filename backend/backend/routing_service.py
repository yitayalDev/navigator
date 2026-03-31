"""
Routing Service Module for UOG Student Navigation
Uses OSRM (Open Source Routing Machine) for shortest path calculations

This module provides:
- Shortest path calculation between coordinates
- Turn-by-turn directions
- Route distance and duration calculation
"""
import os
import requests
import json
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)


class RoutingService:
    """
    Routing service using OSRM for shortest path calculations.
    Can be configured to use a custom SDMR server.
    """
    
    # Default OSRM server (public demo server)
    DEFAULT_OSRM_SERVER = "http://router.project-osrm.org"
    
    # Get SDMR server from config or use default
    SDMR_SERVER: str = os.getenv('SDMR_SERVER', DEFAULT_OSRM_SERVER)
    
    @classmethod
    def get_route(cls, origin: str, destination: str, mode: str = 'foot') -> Optional[Dict]:
        """
        Get the shortest route between two points using OSRM.
        
        Args:
            origin: Starting coordinates as "lat,lng" (e.g., "12.5980,37.3900")
            destination: Ending coordinates as "lat,lng" (e.g., "12.5985,37.3905")
            mode: Transportation mode - 'driving', 'foot', 'cycling' (default: 'foot' for walking)
        
        Returns:
            Dictionary with route information or None if failed
        """
        try:
            # Format coordinates for OSRM (lng,lat format)
            origin_formatted = cls._format_coords(origin)
            destination_formatted = cls._format_coords(destination)
            
            # Map mode to OSRM profile
            profile = 'foot'  # Walking - best for campus navigation
            if mode == 'driving':
                profile = 'driving'
            elif mode == 'cycling':
                profile = 'cycling'
            
            # Build the API URL for shortest path (route) - using foot profile for walking
            url = f"{cls.SDMR_SERVER}/route/v1/{profile}/{origin_formatted};{destination_formatted}"
            params = {
                'overview': 'full',
                'geometries': 'geojson',
                'steps': 'true',
                'annotations': 'true',
                'continue_straight': 'true'
            }
            
            print(f"[OSRM] Requesting route from {origin} to {destination}")
            print(f"[OSRM] URL: {url}")
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                print(f"[OSRM] Response code: {data.get('code')}")
                
                if data.get('code') == 'Ok' and data.get('routes'):
                    route = data['routes'][0]
                    return {
                        'distance': route['distance'],  # meters
                        'duration': route['duration'],  # seconds
                        'geometry': route['geometry'],  # GeoJSON
                        'legs': route['legs'],
                        'summary': route.get('summary', ''),
                        'profile': profile
                    }
                else:
                    print(f"[OSRM] No route found: {data.get('message', 'Unknown error')}")
            
            return None
            
        except requests.exceptions.Timeout:
            print("[OSRM] Request timeout")
            return None
        except requests.exceptions.ConnectionError:
            print("[OSRM] Connection error - server may be down")
            return None
        except Exception as e:
            print(f"[OSRM] Error getting route: {e}")
            return None
    
    @classmethod
    def get_shortest_path(cls, origin: str, destination: str) -> Optional[Dict]:
        """
        Get the shortest path between two points using SDMR server.
        Uses walking mode for pedestrian-friendly routes on campus.
        Falls back to direct distance if OSRM doesn't have route data.
        """
        # Try OSRM with foot profile
        route = cls.get_route(origin, destination, mode='foot')
        
        if not route:
            # Fallback to driving profile
            route = cls.get_route(origin, destination, mode='driving')
        
        # Check if route is valid (has actual distance)
        if route and route.get('distance', 0) > 0:
            return route
        
        # If OSRM returns 0 distance, calculate direct distance as fallback
        direct_distance = cls.calculate_distance(origin, destination)
        if direct_distance:
            # Estimate walking time (average 5 km/h = 83.33 m/min)
            duration = (direct_distance / 83.33) * 60
            
            return {
                'distance': direct_distance,
                'duration': duration,
                'geometry': None,
                'legs': [],
                'summary': 'Direct path (no road data available)',
                'profile': 'foot',
                'is_fallback': True
            }
        
        return None
    
    @classmethod
    def get_directions(cls, origin: str, destination: str) -> Optional[str]:
        """
        Get turn-by-turn directions as a formatted string.
        
        Args:
            origin: Starting coordinates as "lat,lng"
            destination: Ending coordinates as "lat,lng"
        
        Returns:
            Formatted string with directions or None if failed
        """
        route = cls.get_route(origin, destination)
        
        if not route:
            return None
        
        # Format the response
        distance_km = route['distance'] / 1000
        duration_min = route['duration'] / 60
        
        directions = f"📏 *Distance:* {distance_km:.2f} km\n"
        directions += f"⏱️ *Duration:* {duration_min:.1f} minutes\n"
        directions += f"🚶 *Mode:* Walking (Shortest Path)\n\n"
        directions += "🛤️ *Turn-by-turn directions:*\n\n"
        
        step_num = 1
        for leg in route['legs']:
            for step in leg['steps']:
                # Build instruction from maneuver
                maneuver = step.get('maneuver', {})
                maneuver_type = maneuver.get('type', '')
                maneuver_modifier = maneuver.get('modifier', '')
                
                # Create human-readable instruction
                instruction = cls._format_maneuver(maneuver_type, maneuver_modifier)
                
                distance = step.get('distance', 0)
                name = step.get('name', 'unnamed path')
                
                if instruction:
                    directions += f"{step_num}. {instruction}\n"
                    directions += f"   📍 {name} - {distance:.0f}m\n\n"
                    step_num += 1
        
        return directions
    
    @classmethod
    def _format_maneuver(cls, maneuver_type: str, modifier: str) -> str:
        """Format maneuver type and modifier into human-readable instruction."""
        maneuvers = {
            'depart': "Start walking",
            'arrive': "You have arrived",
            'turn': {
                'right': "Turn right",
                'left': "Turn left",
                'slight right': "Bear right",
                'slight left': "Bear left",
                'sharp right': "Sharp right",
                'sharp left': "Sharp left",
                'uturn': "Make a U-turn"
            },
            'new name': "Continue on",
            'depart': "Head to",
            'merge': "Merge onto",
            'on ramp': "Take the ramp",
            'off ramp': "Exit",
            'fork': {
                'right': "Keep right at fork",
                'left': "Keep left at fork",
                'slight right': "Bear right at fork",
                'slight left': "Bear left at fork"
            },
            'end of road': {
                'right': "Turn right at the end",
                'left': "Turn left at the end"
            },
            'roundabout': "Enter roundabout",
            'rotary': "Enter rotary",
            'roundabout turn': "Exit roundabout",
            'notification': "Note:",
            'exit roundabout': "Exit roundabout"
        }
        
        if maneuver_type in maneuvers:
            result = maneuvers[maneuver_type]
            if isinstance(result, dict) and modifier:
                return result.get(modifier, f"{maneuver_type} {modifier}")
            return result
        
        return f"{maneuver_type} {modifier}".strip()
    
    @classmethod
    def get_route_geojson(cls, origin: str, destination: str) -> Optional[str]:
        """
        Get route as GeoJSON for displaying on map.
        
        Args:
            origin: Starting coordinates as "lat,lng"
            destination: Ending coordinates as "lat,lng"
        
        Returns:
            GeoJSON string or None if failed
        """
        route = cls.get_route(origin, destination)
        
        if route and 'geometry' in route:
            return json.dumps(route['geometry'])
        
        return None
    
    @classmethod
    def _format_coords(cls, coords: str) -> str:
        """
        Convert coordinates from "lat,lng" to "lng,lat" format for OSRM.
        
        Args:
            coords: Coordinates in "lat,lng" format
        
        Returns:
            Coordinates in "lng,lat" format
        """
        try:
            lat, lng = coords.split(',')
            return f"{lng.strip()},{lat.strip()}"
        except:
            return coords
    
    @classmethod
    def calculate_distance(cls, origin: str, destination: str) -> Optional[float]:
        """
        Calculate straight-line distance between two points.
        
        Args:
            origin: Starting coordinates as "lat,lng"
            destination: Ending coordinates as "lat,lng"
        
        Returns:
            Distance in meters or None if failed
        """
        try:
            lat1, lng1 = map(float, origin.split(','))
            lat2, lng2 = map(float, destination.split(','))
            
            # Haversine formula for distance
            from math import radians, cos, sin, asin, sqrt
            
            lon1, lat1, lon2, lat2 = map(radians, [lng1, lat1, lng2, lat2])
            
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            
            # Radius of earth in meters
            r = 6371000
            
            return c * r
            
        except Exception as e:
            print(f"Error calculating distance: {e}")
            return None


# Export routing service
routing_service = RoutingService

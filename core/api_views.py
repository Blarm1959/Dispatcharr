# core/api_views.py

import json
import ipaddress
import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, action
from drf_yasg.utils import swagger_auto_schema
from .models import (
    UserAgent,
    StreamProfile,
    CoreSettings,
    STREAM_HASH_KEY,
    NETWORK_ACCESS,
    PROXY_SETTINGS_KEY,
)
from .serializers import (
    UserAgentSerializer,
    StreamProfileSerializer,
    CoreSettingsSerializer,
    ProxySettingsSerializer,
)

import socket
import requests
import os
from core.tasks import rehash_streams
from apps.accounts.permissions import (
    Authenticated,
)
from dispatcharr.utils import get_client_ip


logger = logging.getLogger(__name__)


class UserAgentViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows user agents to be viewed, created, edited, or deleted.
    """

    queryset = UserAgent.objects.all()
    serializer_class = UserAgentSerializer


class StreamProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows stream profiles to be viewed, created, edited, or deleted.
    """

    queryset = StreamProfile.objects.all()
    serializer_class = StreamProfileSerializer


class CoreSettingsViewSet(viewsets.ModelViewSet):
    """
    API endpoint for editing core settings.
    This is treated as a singleton: only one instance should exist.
    """

    queryset = CoreSettings.objects.all()
    serializer_class = CoreSettingsSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        response = super().update(request, *args, **kwargs)
        if instance.key == STREAM_HASH_KEY:
            if instance.value != request.data["value"]:
                rehash_streams.delay(request.data["value"].split(","))

        return response
    @action(detail=False, methods=["post"], url_path="check")
    def check(self, request, *args, **kwargs):
        data = request.data

        if data.get("key") == NETWORK_ACCESS:
            client_ip = ipaddress.ip_address(get_client_ip(request))

            in_network = {}
            invalid = []

            value = json.loads(data.get("value", "{}"))
            for key, val in value.items():
                in_network[key] = []
                cidrs = val.split(",")
                for cidr in cidrs:
                    try:
                        network = ipaddress.ip_network(cidr)

                        if client_ip in network:
                            in_network[key] = []
                            break

                        in_network[key].append(cidr)
                    except:
                        invalid.append(cidr)

            if len(invalid) > 0:
                return Response(
                    {
                        "error": True,
                        "message": "Invalid CIDR(s)",
                        "data": invalid,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(in_network, status=status.HTTP_200_OK)

        return Response({}, status=status.HTTP_200_OK)

class ProxySettingsViewSet(viewsets.ViewSet):
    """
    API endpoint for proxy settings stored as JSON in CoreSettings.
    """
    serializer_class = ProxySettingsSerializer

    def _get_or_create_settings(self):
        """Get or create the proxy settings CoreSettings entry"""
        try:
            settings_obj = CoreSettings.objects.get(key=PROXY_SETTINGS_KEY)
            settings_data = json.loads(settings_obj.value)
        except (CoreSettings.DoesNotExist, json.JSONDecodeError):
            # Create default settings
            settings_data = {
                "buffering_timeout": 15,
                "buffering_speed": 1.0,
                "redis_chunk_ttl": 60,
                "channel_shutdown_delay": 0,
                "channel_init_grace_period": 5,
            }
            settings_obj, created = CoreSettings.objects.get_or_create(
                key=PROXY_SETTINGS_KEY,
                defaults={
                    "name": "Proxy Settings",
                    "value": json.dumps(settings_data)
                }
            )
        return settings_obj, settings_data

    def list(self, request):
        """Return proxy settings"""
        settings_obj, settings_data = self._get_or_create_settings()
        return Response(settings_data)

    def retrieve(self, request, pk=None):
        """Return proxy settings regardless of ID"""
        settings_obj, settings_data = self._get_or_create_settings()
        return Response(settings_data)

    def update(self, request, pk=None):
        """Update proxy settings"""
        settings_obj, current_data = self._get_or_create_settings()

        serializer = ProxySettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update the JSON data
        settings_obj.value = json.dumps(serializer.validated_data)
        settings_obj.save()

        return Response(serializer.validated_data)

    def partial_update(self, request, pk=None):
        """Partially update proxy settings"""
        settings_obj, current_data = self._get_or_create_settings()

        # Merge current data with new data
        updated_data = {**current_data, **request.data}

        serializer = ProxySettingsSerializer(data=updated_data)
        serializer.is_valid(raise_exception=True)

        # Update the JSON data
        settings_obj.value = json.dumps(serializer.validated_data)
        settings_obj.save()

        return Response(serializer.validated_data)

    @action(detail=False, methods=['get', 'patch'])
    def settings(self, request):
        """Get or update the proxy settings."""
        if request.method == 'GET':
            return self.list(request)
        elif request.method == 'PATCH':
            return self.partial_update(request)



@swagger_auto_schema(
    method="get",
    operation_description="Endpoint for environment details",
    responses={200: "Environment variables"},
)
@api_view(["GET"])
@permission_classes([Authenticated])
def environment(request):
    public_ip = None
    local_ip = None
    country_code = None
    country_name = None

    # 1) Get the public IP from ipify.org API
    try:
        r = requests.get("https://api64.ipify.org?format=json", timeout=5)
        r.raise_for_status()
        public_ip = r.json().get("ip")
    except requests.RequestException as e:
        public_ip = f"Error: {e}"

    # 2) Get the local IP by connecting to a public DNS server
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # connect to a "public" address so the OS can determine our local interface
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception as e:
        local_ip = f"Error: {e}"

    # 3) Get geolocation data from ipapi.co or ip-api.com
    if public_ip and "Error" not in public_ip:
        try:
            # Attempt to get geo information from ipapi.co first
            r = requests.get(f"https://ipapi.co/{public_ip}/json/", timeout=5)

            if r.status_code == requests.codes.ok:
                geo = r.json()
                country_code = geo.get("country_code")  # e.g. "US"
                country_name = geo.get("country_name")  # e.g. "United States"

            else:
                # If ipapi.co fails, fallback to ip-api.com
                # only supports http requests for free tier
                r = requests.get("http://ip-api.com/json/", timeout=5)

                if r.status_code == requests.codes.ok:
                    geo = r.json()
                    country_code = geo.get("countryCode")  # e.g. "US"
                    country_name = geo.get("country")  # e.g. "United States"

                else:
                    raise Exception("Geo lookup failed with both services")

        except Exception as e:
            logger.error(f"Error during geo lookup: {e}")
            country_code = None
            country_name = None

    # 4) Get environment mode from system environment variable
    return Response(
        {
            "authenticated": True,
            "public_ip": public_ip,
            "local_ip": local_ip,
            "country_code": country_code,
            "country_name": country_name,
            "env_mode": "dev" if os.getenv("DISPATCHARR_ENV") == "dev" else "prod",
        }
    )


@swagger_auto_schema(
    method="get",
    operation_description="Get application version information",
    responses={200: "Version information"},
)

@api_view(["GET"])
def version(request):
    # Import version information
    from version import __version__, __timestamp__

    return Response(
        {
            "version": __version__,
            "timestamp": __timestamp__,
        }
    )


@swagger_auto_schema(
    method="get",
    operation_description="Fetch latest GitHub release info for Dispatcharr",
    responses={200: "Latest release information"},
)
@api_view(["GET"])
def latest_release(request):
    """Return information about the latest GitHub release and whether it's newer than current."""
    from version import __version__ as current_version

    api_url = "https://api.github.com/repos/Dispatcharr/Dispatcharr/releases/latest"
    try:
        r = requests.get(
            api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Dispatcharr",
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"Failed to fetch latest release: {e}")
        return Response(
            {
                "current_version": current_version,
                "latest_version": current_version,
                "latest_url": None,
                "is_newer": False,
                "error": True,
                "message": "Unable to check GitHub releases",
            }
        )

    tag = data.get("tag_name") or data.get("name") or ""
    latest_version = str(tag).lstrip("vV").strip() or current_version

    def parse_ver(v: str):
        parts = []
        for p in v.split("."):
            try:
                parts.append(int(p))
            except Exception:
                # Strip non-digits prefix/suffix like rc, beta
                num = "".join(ch for ch in p if ch.isdigit())
                parts.append(int(num) if num else 0)
        # Normalize length
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])

    try:
        is_newer = parse_ver(latest_version) > parse_ver(current_version)
    except Exception:
        is_newer = latest_version != current_version

    return Response(
        {
            "current_version": current_version,
            "latest_version": latest_version,
            "latest_url": data.get("html_url"),
            "is_newer": bool(is_newer),
            "published_at": data.get("published_at"),
            "release_name": data.get("name"),
            "prerelease": data.get("prerelease", False),
        }
    )

@swagger_auto_schema(
    method="post",
    operation_description="Trigger rehashing of all streams",
    responses={200: "Rehash task started"},
)
@api_view(["POST"])
@permission_classes([Authenticated])
def rehash_streams_endpoint(request):
    """Trigger the rehash streams task"""
    try:
        # Get the current hash keys from settings
        hash_key_setting = CoreSettings.objects.get(key=STREAM_HASH_KEY)
        hash_keys = hash_key_setting.value.split(",")
        
        # Queue the rehash task
        task = rehash_streams.delay(hash_keys)
        
        return Response({
            "success": True,
            "message": "Stream rehashing task has been queued",
            "task_id": task.id
        }, status=status.HTTP_200_OK)
        
    except CoreSettings.DoesNotExist:
        return Response({
            "success": False,
            "message": "Hash key settings not found"
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error triggering rehash streams: {e}")
        return Response({
            "success": False,
            "message": "Failed to trigger rehash task"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

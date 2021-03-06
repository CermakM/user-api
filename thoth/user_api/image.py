#!/usr/bin/env python3
# thoth-user-api
# Copyright(C) 2018 Fridolin Pokorny
#
# This program is free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Manipulation with images - routines for image checks and first inspections."""

import logging

from thoth.analyzer import run_command

from .configuration import Configuration
from .exceptions import ImageError
from .exceptions import ImageManifestUnknownError
from .exceptions import ImageAuthenticationRequired

_LOGGER = logging.getLogger(__name__)

# To be consistent with API responses - we always return snake case on API.
# These values are actually keys as returned by skopeo.
_TRANSLATION_TABLE = {
    "Name": "name",
    "Tag": "tag",
    "Digest": "digest",
    "RepoTags": "repo_tags",
    "Created": "created",
    "DockerVersion": "docker_version",
    "Labels": "labels",
    "Architecture": "architecture",
    "Os": "os",
    "Layers": "layers"
}


def get_image_metadata(image_name: str, *,
                       registry_user: str = None, registry_password: str = None, verify_tls: bool = True) -> dict:
    """Get metadata for the given image and image repository."""
    if not registry_user and not registry_password:
        cmd = f'skopeo inspect docker://{image_name!r}'
    elif registry_user and registry_password:
        # TODO: make sure registry_user and registry_password get escaped.
        cmd = f'skopeo inspect --creds={registry_user}:{registry_password} docker://{image_name!r}'
    else:
        raise NotImplementedError(
            "Both parameters registry_user and registry_password have to be supplied for registry authentication"
        )

    if not verify_tls:
        cmd += ' --src-tls-verify=false'

    result = run_command(cmd, is_json=True, raise_on_error=False)

    if result.return_code == 0:
        result_dict = {}
        for key, value in result.stdout.items():
            result_dict[_TRANSLATION_TABLE[key]] = value

        return result_dict

    if 'manifest unknown' in result.stderr:
        raise ImageManifestUnknownError("Unknown manifest for the given image")
    elif 'unauthorized: authentication required' in result.stderr:
        raise ImageAuthenticationRequired("There is required authentication in order to pull image and image details")

    _LOGGER.warning("An unhandled error occurred during extraction of image %r: %s", image_name, result.stderr)
    raise ImageError(
        "There was an error when extracting image information, please contact administrator for more details"
    )

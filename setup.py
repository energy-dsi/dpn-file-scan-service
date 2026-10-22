from setuptools import find_namespace_packages, setup

setup(
    name="file-scan-app",
    version="1.0.0",
    description="File scan service (multi-cloud: AWS / Azure / GCP).",
    license="Apache-2.0",
    license_files=["LICENSE.md", "NOTICE.md"],
    # The provider/config/api subpackages are PEP 420 namespace packages
    # (no __init__.py), so use find_namespace_packages to include them.
    packages=find_namespace_packages(include=["app", "app.*"]),
)

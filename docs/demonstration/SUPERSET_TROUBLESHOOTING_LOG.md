# 🐞 Superset Troubleshooting Log: Hive Driver Issues

## 🛑 The Problem
**Error**: `Could not load database driver: HiveEngineSpec` and `ImpalaEngineSpec`.
**Impact**: Unable to connect Apache Superset to the Spark Thrift Server (Hive Interface) to visualize data.

## 🔍 Root Cause Analysis
This error is misleading. It usually means one of three things:
1.  **Missing Python Libraries**: The `pyhive`, `thrift`, or `sasl` libraries are absent.
2.  **OS Dependency Missing**: The `sasl` library requires C++ compilers (`gcc`, `libsasl2-dev`) to build.
3.  **Version Incompatibility**: Newer `thrift` versions (0.22+) break compatibility with `pyhive` (requires 0.16.0).
4.  **Permissions**: Libraries installed by `root` were not readable by the `superset` runtime user.

## 🛠️ Attempts & Fixes Applied

### Attempt 1: Runtime Installation (Failed)
*   **Action**: Ran `pip install pyhive` inside the running container.
*   **Result**: Failed building `sasl` wheel due to missing `gcc`.
*   **Fix**: Installed `build-essential` and `libsasl2-dev`.
*   **Outcome**: Driver installed, but `root` ownership prevented Superset from loading it.

### Attempt 2: Permission Fix (Partial Success)
*   **Action**: Ran `chmod -R 755` on the site-packages directory.
*   **Result**: Python could import the module manually (`import pyhive`), but Superset UI still errored.

### Attempt 3: Custom Docker Image (Definitive Architecture)
*   **Action**: Created a custom `Dockerfile` to bake dependencies into the image at build time.
*   **Pinning**: Explicitly pinned `thrift==0.16.0` to ensure compatibility.
*   **Rebuild**: Executed a `no-cache` rebuild of the container.
*   **Verification**: `pip list` confirms `thrift 0.16.0` and `pyhive` are present.

## ⚠️ Current Status
Despite having a pristine environment (Verified `pyhive` and `thrift` 0.16.0 exist), Superset continues to throw the `HiveEngineSpec` error.
This suggests **Hive Thrift support is deprecated/flaky** in the latest Superset versions or requires deeper configuration changes (Feature Flags).

## 🚀 Recommended Next Step: Switch to Trino
Instead of fighting the legacy Hive Driver, we should use **Trino** (which is already part of our architecture).
*   **Why?**: Trino is the modern standard for querying Iceberg/Nessie. It has a native, stable Superset driver (`trino://`).
*   **Action**: Check if the Trino container is running and connect using `trino://140.238.224.207:8080`.

# Linux Wireless Architecture and nl80211

This report breaks down the Linux wireless subsystem architecture, specifically focusing on the `nl80211.c` module, the `NL80211_CMD_GET_KEY` Netlink command, and the `nl80211_get_key` kernel function.

---

## 1. The High-Level Architecture

The Linux wireless networking stack is designed in layers to abstract hardware complexities away from user applications. 

> [!NOTE]
> **The Wireless Stack Flow:**
> **Userspace** `(wpa_supplicant, iw)` ⟷ **Netlink Interface** `(nl80211)` ⟷ **Control Plane** `(cfg80211)` ⟷ **MAC Plane** `(mac80211)` ⟷ **Hardware Driver**

### Components:
*   **Userspace Tools:** Applications like `wpa_supplicant` (handles WPA/WPA2/WPA3 authentication) and `iw` (command-line configuration tool) do not talk directly to hardware. They talk to the kernel via socket communication.
*   **Netlink (`nl80211`):** A socket-based IPC (Inter-Process Communication) mechanism. Generic Netlink is used to send standardized wireless commands between userspace and the kernel.
*   **`cfg80211`:** The kernel's central wireless configuration API. It keeps track of all wireless devices, handles regulatory domains, and manages network interfaces.
*   **`mac80211`:** A software framework that implements the 802.11 Media Access Control (MAC) protocols for "SoftMAC" devices (devices where the firmware is too simple to handle things like beaconing or packet aggregation on its own).
*   **Driver:** The hardware-specific code that pushes bits to the actual Wi-Fi chip.

---

## 2. The `nl80211.c` Module

The file `net/wireless/nl80211.c` is part of the `cfg80211` subsystem. It acts as the **front door** to the Linux kernel's wireless stack.

### Key Responsibilities:
1.  **Command Dispatch:** It registers a family of Generic Netlink commands (e.g., `NL80211_CMD_GET_WIPHY`, `NL80211_CMD_AUTHENTICATE`, `NL80211_CMD_GET_KEY`). When userspace sends a `sendmsg` containing one of these commands, the kernel routes it to the matching handler in this file.
2.  **Input Validation:** Before executing a command, it sanitizes inputs using pre-hooks (like the `nl80211_pre_doit` we saw earlier). It ensures that:
    *   The requested wireless device exists and is powered on.
    *   The caller has the required permissions (`CAP_NET_ADMIN`).
    *   The Netlink attributes (parameters) are well-formed.
3.  **Routing to `mac80211` or Drivers:** After validating the request, `nl80211.c` invokes the appropriate `cfg80211` internal functions or hardware driver callbacks (`rdev->ops`) to do the actual work.

---

## 3. The `sendmsg$NL80211_CMD_GET_KEY` Syscall

In the context of Syzkaller (or any userspace C program), this pseudo-syscall represents a process sending a `sendmsg` system call over a Netlink socket.

### Purpose:
The `NL80211_CMD_GET_KEY` command is an administrative request from userspace asking the kernel to return the security key sequence parameters (like WEP, WPA-TKIP, or CCMP sequence counters) currently programmed into the hardware or software encryption engine. 

### Why would userspace ask for this?
Userspace daemons like `wpa_supplicant` or `hostapd` sometimes need to retrieve the key sequence numbers. For example, if a station is roaming or a key is being rotated, the daemon needs to know the exact packet sequence number the hardware was currently on to ensure replay-protection (preventing attackers from replaying old packets) isn't broken during the transition.

---

## 4. The `nl80211_get_key` Function

Once the generic netlink subsystem parses `NL80211_CMD_GET_KEY` and validates its parameters via `nl80211_pre_doit`, execution lands in `nl80211_get_key`.

### Step-by-Step Execution:
1.  **Parsing Parameters:** It extracts the requested `key_idx` (e.g., Key index 0 to 3 for WEP/WPA) and the `mac_addr` (if it's a pairwise key meant for a specific client) from the incoming Netlink attributes.
2.  **Validation Check:** It verifies if the key is pairwise or a group key, and checks if the underlying hardware driver even supports retrieving keys (`if (!rdev->ops->get_key) return -EOPNOTSUPP;`).
3.  **Calling the Driver:** It calls into the hardware-specific (or `mac80211`-specific) callback function: `rdev->ops->get_key()`.
    *   The driver queries its registers or software states and populates a buffer with the key sequence number and cipher suite.
    *   *(Note: For security reasons, modern drivers typically **do not** return the actual secret key payload back to userspace, only the sequence counters and cipher type).*
4.  **Packing the Reply:** It allocates a new Netlink message (`nlmsg_new`), constructs a response payload containing the retrieved key data (`NL80211_ATTR_KEY_SEQ`, `NL80211_ATTR_KEY_CIPHER`), and sends it back over the socket to the userspace process that initiated the request.

# SN_AayushShinde
The Personal Home Cloud is a secure, role-based storage system for families. It provides multi-level access (self, parent, sibling, guest), with files encrypted using Fernet for privacy. A Flask API manages permissions and guest sessions with time limits. Designed for simplicity, security, and extendable remote access.




# Home Cloud Setup with Proxmox, VLANs, and Nextcloud

## Phase 1: Hardware Setup

### Requirements
- **Beelink mini-PC with an N100 CPU** (or similar)
- **USB stick**: 8GB+ to flash Proxmox ISO
- **Client PC**: To prepare boot media and access web UI
- **Proxmox VE ISO Installer**

### Boot Mini-PC from USB
1. Plug in USB and keyboard/monitor.
2. Enter BIOS (usually Del or F7 for Beelink).
3. Disable **Secure Boot**.
4. Enable **Virtualization (VT-x/AMD-V, IOMMU)**.
5. Set USB as first boot device.

### Install Proxmox VE
1. Boot into installer → select **Install Proxmox VE**.
2. Choose target disk (your NVMe/SSD).
3. Configure:
   - Filesystem: **ext4** or **ZFS** (ZFS if you want snapshots, but needs more RAM)
   - Country/keyboard/timezone
   - Management interface: choose your Ethernet NIC
   - Root password + email
   - IP address (static recommended, e.g., 192.168.1.100)
4. Complete installation → reboot → remove USB.

### First Login
- On another PC, open browser: `https://<Proxmox-IP>:8006`
- Example: `https://192.168.1.100:8006`
- Login as root with password set during installation.

---

## Phase 2: Network Security & Segmentation

### 1. Network Segmentation (The "How")
- **VLANs (Virtual LANs):** Configure your capable router (e.g., running OPNsense/pfSense, or a prosumer model like Ubiquiti) to create VLANs.
  - **VLAN 10 - Trusted LAN:** For your personal computers and phones.
  - **VLAN 20 - Server VLAN:** Where your Proxmox host and services will live. *No devices other than the server itself should be on this VLAN.*
  - **VLAN 30 - Guest IoT VLAN:** For visiting relatives and friends. This VLAN should have **no access** to the Server VLAN or Trusted LAN.

### 2. Firewall Rules (The "Controls")
- Create strict firewall rules between VLANs:
  - **Trusted LAN → Server VLAN:** Allow HTTPS (443) to the web interface, and perhaps specific ports for other services. *Deny all else.*
  - **Guest IoT VLAN → Anywhere:** Allow only DNS and internet access. **Explicitly block all traffic to the Server and Trusted LANs.**

### 3. Secure Remote Access (The "Remote Accessibility")
Set up a **VPN Server** on your firewall (OPNsense/pfSense have built-in WireGuard/OpenVPN support) or in a dedicated container on your server.
- **WireGuard** is modern, fast, and simple. Users will install the WireGuard app on their phones/laptops.
- When you want to access your cloud remotely, you first connect to your home VPN. Your device will then act as if it's on your **Trusted LAN**, and you can access your cloud server securely via its private IP address.

---

### Step 1: Create VLAN-aware bridge in Proxmox

Edit `/etc/network/interfaces` (or use web UI):

```
auto vmbr1
iface vmbr1 inet manual
bridge-ports none
bridge-stp off
bridge-fd 0
bridge-vlan-aware yes
```

This bridge (vmbr1) will be used for pfSense LAN.  
VMs/Containers can attach to it with specific VLAN tags.

---

### Step 2: Configure pfSense VLAN interfaces

Inside pfSense (after basic setup):

1. Go to **Interfaces → Assignments → VLANs → Add**.
   - Parent interface = LAN NIC (vmbr1)
   - VLAN 10 (Trusted LAN)
   - VLAN 20 (Server VLAN)
   - VLAN 30 (Guest/IoT VLAN)

2. Go to **Interfaces → Assignments** → Add new VLAN interfaces.
   - LAN_VLAN10 = 192.168.10.1/24
   - SERVER_VLAN20 = 192.168.20.1/24
   - GUEST_VLAN30 = 192.168.30.1/24

3. Enable **DHCP** on each VLAN (Services → DHCP Server).
   - VLAN 10 → Trusted clients (PCs/phones)
   - VLAN 20 → Only Proxmox host & VMs
   - VLAN 30 → Guest IoT

---

### Step 3: Firewall rules in pfSense

Go to **Firewall → Rules → [select VLAN interface]** and add rules:

#### VLAN 10 (Trusted LAN → Server VLAN)
- **Allow**: VLAN 10 → VLAN 20, TCP 443 (Nextcloud, Web UI)
- **Deny**: Everything else (default block)

#### VLAN 20 (Server VLAN)
- **Allow**: Outbound → Internet (ports 80/443, APT updates)
- **Block**: VLAN 20 → VLAN 10 and VLAN 30 (internal isolation)

#### VLAN 30 (Guest/IoT VLAN)
- **Allow**: VLAN 30 → Internet (TCP/UDP 80, 443, DNS 53)
- **Block**: VLAN 30 → VLAN 10 & VLAN 20
- **Optional**: Rate-limit guest bandwidth (traffic shaper)

---

### Step 4: Tag VLANs in Proxmox VMs

When adding a VM NIC in Proxmox:
- Hardware → Network Device → Bridge = vmbr1
- VLAN Tag = 20 (for server VM), 10 (for trusted VM), or 30 (for guest IoT VM)

Example (CLI):
```
qm set 101 --net0 virtio,bridge=vmbr1,tag=20
```

---

### Step 5: Extend VLANs to Wi-Fi & Switch

If you want VLANs beyond Proxmox:
- Configure your managed switch/AP with **802.1q VLANs**
- SSID1 → VLAN 10 (Trusted)
- SSID2 → VLAN 30 (Guest IoT)
- Ethernet port → trunk (all VLANs)

---

## Phase 3: Service Deployment & Access Control

### The "Cloud" Service - Nextcloud:

#### 1. Create LXC container
- In Proxmox web UI → **Create CT**
- Template: Debian 12 standard (download via *Storage → Templates*)
- Resources: 2 CPU / 4 GB RAM (minimum), 50 GB+ disk
- Network: Attach to vmbr1 (LAN/segmented VLAN)

#### 2. Update container
```bash
apt update && apt upgrade -y
```

#### 3. Install stack (LAMP or LEMP)

Here's the **LEMP (Nginx)** version:
```bash
apt install nginx mariadb-server php-fpm php-mysql \
php-xml php-zip php-gd php-curl php-mbstring php-intl unzip -y
```

#### 4. Database for Nextcloud
```sql
mysql -u root -p
CREATE DATABASE nextcloud;
CREATE USER 'ncuser'@'localhost' IDENTIFIED BY 'StrongPassw0rd!';
GRANT ALL PRIVILEGES ON nextcloud.* TO 'ncuser'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### 5. Download Nextcloud
```bash
wget https://download.nextcloud.com/server/releases/latest.zip
unzip latest.zip
mv nextcloud /var/www/
chown -R www-data:www-data /var/www/nextcloud
```

#### 6. Nginx config

Create `/etc/nginx/sites-available/nextcloud.conf`:

```nginx
server {
    listen 80;
    server_name cloud.example.com;
    root /var/www/nextcloud/;
    index index.php index.html;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.2-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
```

Enable site:
```bash
ln -s /etc/nginx/sites-available/nextcloud.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

#### 7. Run installer
Open browser: `http://<LXC-IP>`
- Set admin account
- Enter DB creds (ncuser, nextcloud, password)

#### 8. Secure access
- Use your reverse proxy (Nginx Proxy Manager) to enable **HTTPS + Let's Encrypt**
- Integrate with **Keycloak (OIDC)** for role-based access

---

Run Nextcloud in an LXC container or Docker container on your Proxmox server.

- **Configuration:**
  - Force **HTTPS** using a free certificate from Let's Encrypt
  - This becomes your **"Backend Management"** panel and user portal

---

### 2. Role-Based Access Control (RBAC)

- This is implemented within Nextcloud
  - **Users:** Create users for each family member: alice, bob, mom, dad, guest_jane
  - **Groups:** Create groups: Family, Adults, Kids, Guests
  - **Folder Structure & Permissions:**
    - /Alice (Read-Write for alice, no one else)
    - /Bob (Read-Write for bob, no one else)
    - /Family-Vacation (Read-Write for Adults, Read-Only for Kids)
    - /Public (Read-Only for Guests, Read-Write for Family)

---

### 3. The "Guest Access Portal"

- For visiting friends/relatives, create a user account and add it to the Guests group
- Place files you want to share with them in the /Public folder
- For time-bound access, you can either:
  1. Manually disable the user account in Nextcloud after they leave
  2. Use a script (cron job) that disables users in the Guests group after a certain date

---

## Phase 4: Encryption & Monitoring

### Install Proxmox with LUKS (Option A — recommended)

> **Boot Debian installer** (instead of Proxmox ISO)

- During installation, choose **Guided — use entire disk and set up encrypted LVM**
- Enter a strong passphrase for LUKS
- Debian will create:
  - /boot → unencrypted (needed for bootloader)
  - sda5_crypt → encrypted root with LVM
- Finish Debian install

**Install Proxmox packages on top of Debian**

```bash
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" | sudo tee /etc/apt/sources.list.d/pve-install-repo.list
wget http://download.proxmox.com/debian/proxmox-release-bookworm.gpg -O- | sudo tee /etc/apt/trusted.gpg.d/proxmox-release.gpg
sudo apt update && sudo apt full-upgrade -y
sudo apt install proxmox-ve postfix open-iscsi -y
```

---

### Encrypt additional data volume (Option B)

If Proxmox is already installed:

1. **Identify the target disk**:
   ```bash
   lsblk
   ```

2. **Format with LUKS**:
   ```bash
   sudo cryptsetup luksFormat /dev/sdb
   ```

3. **Open the encrypted device**:
   ```bash
   sudo cryptsetup open /dev/sdb securedata
   ```

4. **Create filesystem**:
   ```bash
   sudo mkfs.ext4 /dev/mapper/securedata
   ```

5. **Mount it**:
   ```bash
   sudo mkdir /mnt/securedata
   sudo mount /dev/mapper/securedata /mnt/securedata
   ```

6. **Configure auto-mount at boot**
   - Get UUID:
     ```bash
     sudo blkid /dev/sdb
     ```
   - Edit `/etc/crypttab`:
     ```
     securedata UUID=<uuid-from-blkid> none luks
     ```
   - Add to `/etc/fstab`:
     ```
     /dev/mapper/securedata /mnt/securedata ext4 defaults 0 2
     ```

7. **Use in Proxmox**  
   In Proxmox web UI → Datacenter → Storage → Add → Directory → point to `/mnt/securedata`  
   Now all VM disks/containers stored here are encrypted at rest.

---


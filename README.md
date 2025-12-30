# TimeTree Calendar for Home Assistant

This is a custom component for **Home Assistant** that integrates with **TimeTree**. It creates a Calendar entity in Home Assistant that syncs with your chosen TimeTree calendar, allowing you to view your upcoming events directly from your dashboard.

The integration fetches events every **60 minutes** and is **read-only** (it does not write back to TimeTree).

---

## 🏆 Credits & Huge Kudos

**Massive thanks to [eoleedi](https://github.com/eoleedi)** for creating the [TimeTree-Exporter](https://github.com/eoleedi/TimeTree-Exporter).

This Home Assistant integration relies heavily on the reverse-engineered API logic and data structures provided by their excellent work. Without `timetree-exporter`, this integration would not be possible!

---

## ✨ Features

* **Calendar Entity**: Adds a standard `calendar` entity to Home Assistant.
* **Auto-Sync**: Polling interval is set to 60 minutes.
* **Multi-Calendar Support**: During setup, you can select which specific TimeTree calendar you want to import.
* **Authentication**: Supports standard Email/Password login.

---

## 📦 Installation

### Option 1: HACS (Recommended)

1.  Open **HACS** in Home Assistant.
2.  Go to **Integrations** > Top right menu (**⋮**) > **Custom repositories**.
3.  Add the URL of this repository.
4.  Category: **Integration**.
5.  Click **Add**, then find **TimeTree Calendar** in the list and click **Download**.
6.  Restart Home Assistant.

### Option 2: Manual Installation

1.  Download this repository.
2.  Copy the `custom_components/timetree` folder.
3.  Paste it into your Home Assistant's `config/custom_components/` directory.
4.  Restart Home Assistant.

---

## ⚙️ Configuration

1.  Navigate to **Settings** > **Devices & Services**.
2.  Click **+ Add Integration**.
3.  Search for **TimeTree Calendar**.
4.  Enter your **TimeTree Email** and **Password**.
5.  If you have multiple calendars, select the one you wish to sync from the dropdown list.
6.  Click **Submit**.

You will now have a new entity (e.g., `calendar.timetree_family`) available in Home Assistant!

---

## ⚠️ Limitations & Notes

* **Read-Only**: This integration is designed to *view* events only. You cannot create or edit TimeTree events from Home Assistant.
* **Polling Rate**: To avoid hitting API rate limits or being flagged, the update frequency is fixed at 60 minutes.
* **Cloud Polling**: This integration requires an active internet connection to fetch data from TimeTree servers.

---


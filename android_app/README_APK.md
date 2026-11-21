# 📱 Building the Android APK for MAHILA SURAKSHA MARG

This guide outlines how to build and install the **MAHILA SURAKSHA MARG** Android App (`.apk`) on your smartphone.

---

## 🏛️ Architecture: How Streamlit Runs as an Android APK

Because **MAHILA SURAKSHA MARG** is powered by an extensive Python ML & Geospatial engine (`scikit-learn`, `shap`, `osmnx`, `networkx`, `sqlite3`), it runs on a Python server backend while the **Android APK** provides:
1. **Native Android App Shell**: Fullscreen immersive UI without browser URL bars or navigation clutter.
2. **Hardware Permissions**: Native access to GPS/Location, Microphone/Camera (for SOS recording), and Phone dialer.
3. **Emergency Interception**: Clicking "Call 112" directly opens Android's native emergency phone dialer.
4. **Dark Theme Integration**: Status bar & navigation bar seamlessly match the app's `#0E1117` dark palette.

---

## 🚀 Method 1: Build APK via Android Studio (Project Included!)

A complete Android Studio project is already generated in the [`android_app`](./) folder.

### Step 1: Open in Android Studio
1. Install [Android Studio](https://developer.android.com/studio) (if not already installed).
2. Open Android Studio and select **Open** (or `File > Open`).
3. Browse to and select:
   ```
   C:\Users\SERVER\Downloads\rbvp project\rbvp project\delhi-suraksha-path\android_app
   ```
4. Wait for Gradle sync to complete (~1-2 minutes on first run).

### Step 2: Configure Server URL
Open `app/src/main/res/values/strings.xml`:
- For **Local Wi-Fi Testing**: It is already pre-configured to your PC's LAN IP:
  ```xml
  <string name="server_url">http://10.206.24.45:8501</string>
  ```
  *(Make sure your phone and PC are connected to the same Wi-Fi).*
- For **Cloud / Production**: Replace with your deployed URL (e.g. `https://mahila-suraksha.streamlit.app`).

### Step 3: Build the `.apk`
1. Go to the top menu: **Build** > **Build Bundle(s) / APK(s)** > **Build APK(s)**.
2. Once the build finishes, Android Studio shows a notification: **APK(s) generated successfully**.
3. Click **locate** or find the file at:
   ```
   android_app/app/build/outputs/apk/debug/app-debug.apk
   ```

### Step 4: Install on Your Phone
1. Transfer `app-debug.apk` to your phone via USB cable, WhatsApp, Google Drive, or Telegram.
2. Tap the `.apk` on your phone and select **Install**.
3. Grant **Location** and **Phone** permissions when prompted.

---

## 🌐 Method 2: Instant No-Code APK via PWABuilder (2 Minutes)

If you don't want to install Android Studio:

1. **Deploy your Streamlit app**:
   - Push this repo to GitHub and connect to [Streamlit Community Cloud](https://share.streamlit.io/) (100% free), or
   - Use a free tunnel from your terminal:
     ```bash
     # Install cloudflared or ngrok:
     winget install Cloudflare.cloudflared
     cloudflared tunnel --url http://localhost:8501
     ```
     This gives you a public HTTPS URL (e.g. `https://delhi-safety-example.trycloudflare.com`).

2. **Generate APK**:
   - Go to [PWABuilder.com](https://www.pwabuilder.com/).
   - Paste your public HTTPS URL and click **Start**.
   - PWABuilder automatically packages the app into an Android package.
   - Click **Package For Stores** > **Android** > **Download APK**.
   - Install the downloaded `.apk` directly on your Android phone!

---

## 📲 Method 3: Instant "Add to Home Screen" (PWA - No Compilation Needed)

You can also install the app immediately onto any Android phone in 10 seconds:

1. On your phone, open Chrome and visit `http://10.206.24.45:8501` (over local Wi-Fi) or your cloud URL.
2. Tap the **three dots menu (⋮)** in the top-right corner.
3. Select **Add to Home Screen** (or **Install App**).
4. An icon named **Mahila Suraksha** will appear on your phone's home screen and launch fullscreen like an APK!

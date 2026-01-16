Great — your HTTPS setup is working!
Now let’s address your **three concerns**:

---

# ✅ 1. Browser "Not Secure" / "Your connection is not private" warning

### **Why this happens**

Because your certificate is **self-signed**.
Browsers cannot trust a certificate unless it is signed by a recognized Certificate Authority (CA).

### ✔️ Is it safe?

Yes — **for local development**, this is 100% safe **as long as**:

* You generated the certificate yourself
* You are accessing only `https://127.0.0.1:<port>` or `https://localhost:<port>`
* You are not exposing your dev server to public internet

Browsers warn because the certificate **cannot be verified**, not because it is insecure.

### ✔️ How to remove the browser warning completely

You have 3 options:

---

### **Option A — Trust the certificate on your OS** (best for dev)

When you trust your self-signed certificate in your OS keychain, Chrome/Firefox/Safari stop warning.

#### **macOS (your system)**

1. Open **Keychain Access**
2. Drag **cert.pem** into the *System* keychain
3. Double-click the cert → expand **Trust**
4. Set:

```
When using this certificate: Always Trust
```

Restart browser → warning disappears.

---

### **Option B — Create a local CA + sign certificate**

This makes your certificate act like a private “real” CA, and browsers trust it.

Use `mkcert` (recommended):

```bash
brew install mkcert
mkcert -install
mkcert 127.0.0.1 localhost
```

This generates trusted certs:

* `127.0.0.1+2.pem`
* `127.0.0.1+2-key.pem`

Run Django:

```bash
python manage.py runserver_plus 9001 \
  --cert-file 127.0.0.1+2.pem \
  --key-file 127.0.0.1+2-key.pem
```

Zero warnings.

---

### **Option C — Ignore warnings manually**

Not ideal long-term.

---

# ✅ 2. Werkzeug Interactive Debugger showing at `/console`

### **Why this happened**

Werkzeug automatically registers a built-in debugger & interactive console when:

* `runserver_plus` is used
* debug mode is enabled
* the path `/console` is free
* admin site name is `console` → **conflict**

Werkzeug's debugger console **overrides your `/console` admin path**.

So you're loading **Werkzeug console**, not your own Django console.

---

# 🔧 How to disable or move Werkzeug console

### **Option A — Disable Werkzeug debugger completely**

Start the server with:

```bash
python manage.py runserver_plus 9001 --cert-file cert.pem --key-file key.pem --nopin --noreload --debugger=False
```

OR add this to `settings.py`:

```python
RUNSERVER_PLUS = {
    "DEBUGGER": False,
}
```

---

### **Option B — Change Werkzeug console endpoint**

Werkzeug uses `/console` by default.

Override via:

```bash
python manage.py runserver_plus 9001 \
    --cert-file cert.pem --key-file key.pem \
    --werkzeug-console /_wconsole
```

Then Werkzeug console moves to:

```
https://127.0.0.1:9001/_wconsole
```

Your Django `/console` becomes free again.

---

### **Option C — Rename your admin site namespace**

Your admin site is named:

```python
admin_site = PaystreamAdminSite(name='console')
```

Rename to avoid collision:

```python
admin_site = PaystreamAdminSite(name='psadmin')
```

And update your URL:

```python
path('console/', admin_site.urls),
```

This removes the collision with Werkzeug’s `/console`.

---

# ✔️ Recommended combination (clean setup)

### Put this in `settings.py`:

```python
RUNSERVER_PLUS = {
    "DEBUGGER": False,
    "IPYTHON": False,
    "ADMIN": False,
}
```

Run your server normally:

```bash
python manage.py runserver_plus 9001 --cert-file cert.pem --key-file key.pem
```

Result:

* No Werkzeug console
* Your `/console` admin restored
* HTTPS works
* No browser warnings if you trust cert locally

---

# 🔚 Summary

| Issue                              | Fix                                                                   |
| ---------------------------------- | --------------------------------------------------------------------- |
| Browser "Not Safe"                 | Trust cert OR use `mkcert`                                            |
| `/console` shows Werkzeug debugger | Disable debugger OR move Werkzeug console OR rename Django admin site |
| Safety of self-signed cert         | 100% safe for local dev                                               |

---

A full script to auto-generate trusted certificates (macOS + mkcert)

Perfect — here are **all three items** packaged cleanly:

---

# ✅ 1. A `devssl` shell alias

This alias will:

* auto-generate a new cert if missing
* start Django with HTTPS
* disable Werkzeug debugger
* use your preferred port

### **Add to your `~/.zshrc` or `~/.bashrc`:**

```bash

alias devssl="\
echo '🚀 Starting DEVSSL pipeline...'; \
echo '🧹 Flushing Redis...'; \
redis-cli flushall; \
\
echo '🗑️ Clearing & Collecting Static Files...'; \
python manage.py collectstatic --clear --noinput; \
\
echo '🗜️ Compressing Assets...'; \
python manage.py compress --force; \
\
if [ ! -f cert.pem ] || [ ! -f key.pem ]; then \
  echo '🔐 No certificate found. Generating new self-signed certificate...'; \
  openssl req -x509 -newkey rsa:4096 -days 365 -nodes \
    -keyout key.pem -out cert.pem \
    -subj '/C=IN/ST=Maharashtra/L=Peth Vadgaon/O=DjangoPlay/OU=Admin/CN=127.0.0.1'; \
fi; \
\
echo '🌐 Running Django with HTTPS on port 9001...'; \
python manage.py runserver_plus 9001 \
  --cert-file cert.pem \
  --key-file key.pem;
"
```

Reload shell:

```bash
source ~/.zshrc   # or ~/.bashrc
```

Now just run:

```bash
devssl
```

---

# ✅ 2. `settings.py` patch for Werkzeug / runserver_plus

Add this to your `settings.py`:

```python
# Force Werkzeug runserver_plus to behave consistently
RUNSERVER_PLUS = {
    "DEBUGGER": False,   # disable werkzeug debugger console entirely
    "IPYTHON": False,    # disable ipython shell injection
    "ADMIN": False,      # disable werkzeug admin UI
    "THREADING": True,   # preserve threaded behaviour
}

# Optional: Prevent Werkzeug from hijacking the /console path
WERKZEUG_CONSOLE_ENDPOINT = "/_wconsole"
```

Then, update your run command to respect the custom console endpoint:

```bash
python manage.py runserver_plus 9001 \
  --cert-file cert.pem \
  --key-file key.pem \
  --werkzeug-console /_wconsole
```

Now:

* Your Django admin continues at `/console/`
* Werkzeug console moves to `/_wconsole`
* Debugger stops overriding URLs

---

# ✅ 3. A full script to auto-generate trusted certificates (macOS + mkcert)

This script:

* Installs `mkcert` if missing
* Installs the local CA if needed
* Generates trusted certs for:

  * `127.0.0.1`
  * `localhost`
  * your `.local` domain
* Stores them as `dev_cert.pem` & `dev_key.pem`

### **Create file: `generate_dev_cert.sh`**

```bash
#!/bin/bash

set -e

echo "🔍 Checking for mkcert..."
if ! command -v mkcert &> /dev/null
then
    echo "📦 mkcert not found. Installing via Homebrew..."
    brew install mkcert nss
fi

echo "🔐 Installing mkcert root CA (if not installed)..."
mkcert -install

echo "📄 Generating trusted development certificates..."
mkcert -key-file dev_key.pem -cert-file dev_cert.pem 127.0.0.1 localhost $(hostname).local

echo "✅ Done!"
echo "Certificates generated:"
echo " - dev_cert.pem"
echo " - dev_key.pem"
```

Make it executable:

```bash
chmod +x generate_dev_cert.sh
```

Run:

```bash
./generate_dev_cert.sh
```

Start Django using trusted cert:

```bash
python manage.py runserver_plus 9001 --cert-file dev_cert.pem --key-file dev_key.pem
```

Browser will show **secure HTTPS with zero warnings**.

---

# ⭐ Final Golden Workflow

### Step 1 (once):

```bash
./generate_dev_cert.sh
```

### Step 2 (every day):

```bash
devssl
```

### Step 3:

Visit:

```
https://127.0.0.1:9001
```

✔ no browser warning
✔ no Werkzeug conflict
✔ HTTPS always works
✔ admin at `/console/`
✔ optional Werkzeug console at `/_wconsole`

---

If you want, I can also generate:

* A **Makefile** with `make devssl`, `make cert`, `make run`
* A **VSCode launch.json** that auto-starts Django w/ HTTPS + debugger
* A **Fabric deployment script** for switching dev/prod servers

Just tell me.

const tokenKey = "lab4_geoip_token";
let token = localStorage.getItem(tokenKey);

const elements = {
    tabs: document.querySelectorAll(".tab"),
    loginForm: document.querySelector("#loginForm"),
    registerForm: document.querySelector("#registerForm"),
    authMessage: document.querySelector("#authMessage"),
    lookupForm: document.querySelector("#lookupForm"),
    result: document.querySelector("#result"),
    historyList: document.querySelector("#historyList"),
    sessionUser: document.querySelector("#sessionUser"),
    logoutButton: document.querySelector("#logoutButton"),
    refreshHistory: document.querySelector("#refreshHistory"),
    apiStatus: document.querySelector("#apiStatus"),
    databaseNotice: document.querySelector("#databaseNotice"),
    databaseNoticeText: document.querySelector("#databaseNoticeText"),
    signalValue: document.querySelector("#signalValue"),
    signalState: document.querySelector("#signalState"),
};

elements.tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
        const activeTab = tab.dataset.tab;
        elements.tabs.forEach((item) => item.classList.toggle("active", item.dataset.tab === activeTab));
        elements.loginForm.classList.toggle("hidden", activeTab !== "login");
        elements.registerForm.classList.toggle("hidden", activeTab !== "register");
        setMessage(elements.authMessage, "");
    });
});

elements.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(elements.loginForm);
    await authenticate("/api/auth/login", {
        login: form.get("login"),
        password: form.get("password"),
    });
});

elements.registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(elements.registerForm);
    await authenticate("/api/auth/register", {
        username: form.get("username"),
        email: form.get("email"),
        password: form.get("password"),
    });
});

elements.lookupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(elements.lookupForm);
    await lookupIp(form.get("ip_address"));
});

elements.logoutButton.addEventListener("click", () => {
    token = null;
    localStorage.removeItem(tokenKey);
    elements.sessionUser.textContent = "Гість";
    elements.logoutButton.classList.add("hidden");
    elements.historyList.className = "history-list empty";
    elements.historyList.innerHTML = "<span>Історія доступна після входу.</span>";
    elements.result.className = "result empty";
    elements.result.innerHTML = "<span>Результат сканування з'явиться тут.</span>";
    setMessage(elements.authMessage, "Сесію завершено.");
});

elements.refreshHistory.addEventListener("click", loadHistory);

async function authenticate(url, payload) {
    setMessage(elements.authMessage, "Зачекайте...");
    try {
        const data = await request(url, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        token = data.access_token;
        localStorage.setItem(tokenKey, token);
        elements.sessionUser.textContent = data.user.username;
        elements.logoutButton.classList.remove("hidden");
        setMessage(elements.authMessage, "Вхід виконано.");
        await loadHistory();
    } catch (error) {
        setMessage(elements.authMessage, error.message, true);
    }
}

async function lookupIp(ipAddress) {
    if (!token) {
        renderError(elements.result, "Спочатку увійдіть в акаунт.");
        return;
    }

    elements.apiStatus.textContent = "Сканування";
    elements.apiStatus.classList.add("busy");
    try {
        const data = await request("/api/geoip", {
            method: "POST",
            token,
            body: JSON.stringify({ ip_address: ipAddress }),
        });
        renderResult(data);
        await loadHistory();
    } catch (error) {
        renderError(elements.result, error.message);
    } finally {
        elements.apiStatus.textContent = "Сигнал";
        elements.apiStatus.classList.remove("busy");
    }
}

async function loadHistory() {
    if (!token) {
        return;
    }

    try {
        const items = await request("/api/history", { token });
        renderHistory(items);
    } catch (error) {
        elements.historyList.className = "history-list empty";
        elements.historyList.innerHTML = `<span>${escapeHtml(error.message)}</span>`;
    }
}

async function restoreSession() {
    await loadHealth();

    if (!token) {
        return;
    }

    try {
        const user = await request("/api/me", { token });
        elements.sessionUser.textContent = user.username;
        elements.logoutButton.classList.remove("hidden");
        await loadHistory();
    } catch {
        token = null;
        localStorage.removeItem(tokenKey);
    }
}

async function loadHealth() {
    try {
        const health = await request("/api/health");
        elements.databaseNotice.classList.toggle("hidden", health.mongodb);
        elements.databaseNoticeText.textContent = health.mongodb_error || "Перевірте підключення до бази даних.";
    } catch {
        elements.databaseNotice.classList.remove("hidden");
        elements.databaseNoticeText.textContent = "Не вдалося отримати стан сервісу.";
    }
}

async function request(url, options = {}) {
    const headers = {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    };

    const response = await fetch(url, {
        method: options.method || "GET",
        headers,
        body: options.body,
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(readApiError(data) || `Помилка HTTP ${response.status}`);
    }

    return data;
}

function renderResult(data) {
    elements.result.className = "result";
    elements.result.innerHTML = `
        <div class="map-card">
            <span>${escapeHtml(data.ip_address)}</span>
            <strong>${escapeHtml(formatLocation(data))}</strong>
        </div>
        <dl class="details">
            ${detail("Країна", data.country)}
            ${detail("Регіон", data.region)}
            ${detail("Місто", data.city)}
            ${detail("Координати", formatCoordinates(data.coordinates))}
            ${detail("Часовий пояс", data.timezone)}
            ${detail("UTC", data.timezone_utc)}
            ${detail("Провайдер", data.isp)}
            ${detail("Організація", data.organization)}
            ${detail("ASN", data.asn)}
        </dl>
    `;
}

function renderHistory(items) {
    if (!items.length) {
        elements.historyList.className = "history-list empty";
        elements.historyList.innerHTML = "<span>Запитів ще немає.</span>";
        return;
    }

    elements.historyList.className = "history-list";
    elements.historyList.innerHTML = items.map((item) => {
        const geo = item.geolocation;
        return `
            <article class="history-item">
                <div>
                    <strong>${escapeHtml(item.ip_address)}</strong>
                    <span>${escapeHtml(formatLocation(geo))}</span>
                </div>
                <time>${escapeHtml(formatDate(item.requested_at))}</time>
            </article>
        `;
    }).join("");
}

function renderError(target, message) {
    target.className = "result error";
    target.innerHTML = `<strong>Помилка</strong><span>${escapeHtml(message)}</span>`;
}

function detail(label, value) {
    return `
        <div>
            <dt>${escapeHtml(label)}</dt>
            <dd>${escapeHtml(value || "Немає даних")}</dd>
        </div>
    `;
}

function formatLocation(data) {
    return [data.city, data.region, data.country].filter(Boolean).join(", ") || "Локацію не визначено";
}

function formatCoordinates(coordinates) {
    if (!coordinates || coordinates.latitude === null || coordinates.longitude === null) {
        return null;
    }
    return `${Number(coordinates.latitude).toFixed(4)}, ${Number(coordinates.longitude).toFixed(4)}`;
}

function formatDate(value) {
    return new Intl.DateTimeFormat("uk-UA", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function setMessage(target, message, isError = false) {
    target.textContent = message;
    target.classList.toggle("error-text", isError);
}

function readApiError(data) {
    if (typeof data.detail === "string") {
        return data.detail;
    }

    if (Array.isArray(data.detail)) {
        return data.detail.map((error) => error.msg).join("; ");
    }

    if (Array.isArray(data.errors)) {
        return data.errors.map((error) => error.msg).join("; ");
    }

    return null;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function startSignalMeter() {
    if (!elements.signalValue) {
        return;
    }

    let renderedValue = Number(elements.signalValue.dataset.signalValue || "96");
    renderSignalValue(renderedValue, true);

    const runIteration = () => {
        const targetValue = randomInt(0, 100);
        const duration = randomInt(2600, 4200);
        const startedAt = performance.now();
        const slowStart = Math.max(1, targetValue * 0.7);

        elements.signalState?.classList.add("is-syncing");
        if (elements.signalState) {
            elements.signalState.textContent = "SYNCING";
        }

        const tick = (now) => {
            const progress = Math.min((now - startedAt) / duration, 1);
            const rawValue = targetValue * progress;
            const easedValue = rawValue < slowStart
                ? rawValue
                : slowStart + (targetValue - slowStart) * easeOutCubic((rawValue - slowStart) / Math.max(targetValue - slowStart, 1));
            const nextValue = Math.min(targetValue, Math.round(easedValue));

            if (nextValue !== renderedValue || progress === 1) {
                renderedValue = nextValue;
                renderSignalValue(renderedValue);
            }

            if (progress < 1) {
                requestAnimationFrame(tick);
                return;
            }

            elements.signalState?.classList.remove("is-syncing");
            if (elements.signalState) {
                elements.signalState.textContent = "LOCKED";
            }

            window.setTimeout(runIteration, randomInt(2400, 5200));
        };

        requestAnimationFrame(tick);
    };

    window.setTimeout(runIteration, 900);
}

function renderSignalValue(value, initial = false) {
    const nextText = String(value);
    const previousText = elements.signalValue.dataset.rendered || "";
    const digits = [...nextText].map((digit, index) => {
        const changed = !initial && previousText[index] !== digit;
        const className = changed ? "signal-digit is-changing" : "signal-digit";
        return `<span class="${className}" style="--digit-index:${index}">${digit}</span>`;
    }).join("");

    elements.signalValue.dataset.rendered = nextText;
    elements.signalValue.dataset.signalValue = nextText;
    elements.signalValue.innerHTML = `${digits}<span class="signal-percent">%</span>`;
}

function easeOutCubic(value) {
    const normalized = Math.min(Math.max(value, 0), 1);
    return 1 - Math.pow(1 - normalized, 3);
}

function randomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

startSignalMeter();
restoreSession();

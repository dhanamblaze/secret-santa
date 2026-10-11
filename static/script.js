/* =========================================================
   CHRISTMAS CHRIS - FESTIVE SECRET SANTA APPLICATION JS
   ========================================================= */

const API_BASE = "";

// State
let authToken = localStorage.getItem("xmas_santa_token") || null;
let currentUser = JSON.parse(localStorage.getItem("xmas_santa_user") || "null");
let currentGroupId = null;

// ================= INITIALIZATION & ROUTING =================

document.addEventListener("DOMContentLoaded", () => {
    initSnowflakes();
    handleInitialRoute();

    // Listen for hash changes
    window.addEventListener("hashchange", handleInitialRoute);
});

function handleInitialRoute() {
    const hash = window.location.hash.replace("#", "") || "";
    
    if (authToken && currentUser) {
        updateNavbarUser(currentUser.username);
        if (hash.startsWith("group/")) {
            const gid = hash.split("/")[1];
            navigate("group", gid);
        } else {
            navigate("dashboard");
        }
    } else {
        updateNavbarUser(null);
        if (hash === "signup") {
            navigate("signup");
        } else {
            navigate("login");
        }
    }
}

function navigate(viewName, param = null) {
    // Hide all views
    document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active"));

    if (viewName === "signup") {
        window.location.hash = "#signup";
        document.getElementById("viewSignup").classList.add("active");
    } else if (viewName === "login") {
        window.location.hash = "#login";
        document.getElementById("viewLogin").classList.add("active");
    } else if (viewName === "dashboard") {
        if (!authToken) return navigate("login");
        window.location.hash = "#dashboard";
        document.getElementById("viewDashboard").classList.add("active");
        loadMyGroups();
    } else if (viewName === "group") {
        if (!authToken) return navigate("login");
        const gid = param || currentGroupId;
        if (!gid) return navigate("dashboard");
        currentGroupId = gid;
        window.location.hash = `#group/${gid}`;
        document.getElementById("viewGroup").classList.add("active");
        loadGroupDetails(gid);
    }
}

function updateNavbarUser(username) {
    const navUserSec = document.getElementById("navUserSection");
    const navUsername = document.getElementById("currentUsername");
    if (username) {
        navUsername.textContent = username;
        navUserSec.style.display = "flex";
    } else {
        navUserSec.style.display = "none";
    }
}

// ================= API REQUEST HELPER =================

async function apiRequest(endpoint, method = "GET", body = null) {
    const headers = {
        "Content-Type": "application/json"
    };

    if (authToken) {
        headers["Authorization"] = `Bearer ${authToken}`;
    }

    const options = {
        method,
        headers
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    try {
        const res = await fetch(`${API_BASE}${endpoint}`, options);
        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
            if (res.status === 401) {
                // Session expired or invalid
                logout(false);
                throw new Error("Session expired. Please log in again.");
            }
            throw new Error(data.detail || data.message || "Something went wrong.");
        }

        return data;
    } catch (err) {
        showToast(err.message, "error");
        throw err;
    }
}

// ================= AUTHENTICATION =================

async function handleSignup(e) {
    e.preventDefault();
    const username = document.getElementById("signupUsername").value.trim();
    const password = document.getElementById("signupPassword").value;
    const confirmPassword = document.getElementById("signupConfirmPassword").value;

    if (!username) {
        showToast("Please enter a username.", "error");
        return;
    }

    if (password.length < 6) {
        showToast("Password must be at least 6 characters long.", "error");
        return;
    }

    if (password !== confirmPassword) {
        showToast("Passwords do not match. Please re-enter.", "error");
        return;
    }

    try {
        const res = await apiRequest("/api/auth/signup", "POST", { username, password });
        showToast(res.message || "Account created successfully! 🎅", "success");
        
        // Auto-login
        authToken = res.token;
        currentUser = res.user;
        localStorage.setItem("xmas_santa_token", authToken);
        localStorage.setItem("xmas_santa_user", JSON.stringify(currentUser));
        
        updateNavbarUser(currentUser.username);
        document.getElementById("signupForm").reset();
        navigate("dashboard");
    } catch (err) {
        // Handled in apiRequest
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value;

    if (!username || !password) {
        showToast("Please enter both username and password.", "error");
        return;
    }

    try {
        const res = await apiRequest("/api/auth/login", "POST", { username, password });
        showToast(res.message || "Welcome back! 🎄", "success");

        authToken = res.token;
        currentUser = res.user;
        localStorage.setItem("xmas_santa_token", authToken);
        localStorage.setItem("xmas_santa_user", JSON.stringify(currentUser));

        updateNavbarUser(currentUser.username);
        document.getElementById("loginForm").reset();
        navigate("dashboard");
    } catch (err) {
        // Handled in apiRequest
    }
}

function logout(showFeedback = true) {
    authToken = null;
    currentUser = null;
    currentGroupId = null;
    localStorage.removeItem("xmas_santa_token");
    localStorage.removeItem("xmas_santa_user");
    updateNavbarUser(null);
    if (showFeedback) {
        showToast("Logged out successfully. Merry Christmas! ❄️", "success");
    }
    navigate("login");
}

// ================= DASHBOARD =================

async function handleCreateGroup(e) {
    e.preventDefault();
    const nameInput = document.getElementById("createGroupName");
    const name = nameInput.value.trim();
    if (!name) return;

    try {
        const res = await apiRequest("/api/groups/create", "POST", { name });
        showToast(res.message || "Group created! 🎁", "success");
        nameInput.value = "";
        navigate("group", res.group.id);
    } catch (err) {
        // Handled in apiRequest
    }
}

async function handleJoinGroup(e) {
    e.preventDefault();
    const codeInput = document.getElementById("joinGroupCode");
    const code = codeInput.value.trim().toUpperCase();
    if (!code) return;

    try {
        const res = await apiRequest("/api/groups/join", "POST", { code });
        showToast(res.message || "Joined group! 🎄", "success");
        codeInput.value = "";
        navigate("group", res.group_id);
    } catch (err) {
        // Handled in apiRequest
    }
}

async function loadMyGroups() {
    const loadingEl = document.getElementById("groupsLoading");
    const emptyEl = document.getElementById("groupsEmpty");
    const listEl = document.getElementById("groupsList");

    loadingEl.style.display = "block";
    emptyEl.style.display = "none";
    listEl.innerHTML = "";

    try {
        const data = await apiRequest("/api/groups/my-groups");
        loadingEl.style.display = "none";

        if (!data.groups || data.groups.length === 0) {
            emptyEl.style.display = "block";
            return;
        }

        data.groups.forEach(group => {
            const card = document.createElement("div");
            card.className = "group-item-card";
            card.onclick = () => navigate("group", group.id);

            const statusBadge = group.is_shuffled 
                ? `<span class="badge-shuffled">🎁 Secret Santas Assigned</span>`
                : `<span class="badge-pending">⏳ Waiting for Shuffle</span>`;

            card.innerHTML = `
                <div>
                    <div class="group-item-top">
                        <div class="group-item-title">${escapeHtml(group.name)}</div>
                        ${statusBadge}
                    </div>
                    <div class="group-item-info">
                        👥 <strong>${group.member_count}</strong> member${group.member_count !== 1 ? 's' : ''} &bull; 
                        ${group.is_creator ? '👑 Admin' : '👤 Member'}
                    </div>
                </div>
                <div>
                    <span class="group-code-pill">Code: ${escapeHtml(group.code)}</span>
                </div>
            `;
            listEl.appendChild(card);
        });
    } catch (err) {
        loadingEl.style.display = "none";
    }
}

// ================= GROUP DETAILS =================

async function loadGroupDetails(groupId) {
    try {
        const data = await apiRequest(`/api/groups/${groupId}`);
        const group = data.group;
        const assignment = data.assignment;
        const members = data.members;
        const myWishlist = data.my_wishlist;

        // Render header info
        document.getElementById("groupDetailName").textContent = group.name;
        document.getElementById("groupDetailCode").textContent = group.code;
        document.getElementById("groupCreatorName").textContent = group.creator_name;
        document.getElementById("myWishlistInput").value = myWishlist || "";

        // Status pill
        const statusPill = document.getElementById("groupStatusPill");
        if (group.is_shuffled) {
            statusPill.innerHTML = `<span class="badge-shuffled">🎅 Shuffled & Active</span>`;
        } else {
            statusPill.innerHTML = `<span class="badge-pending">⏳ Gathering Members (${members.length})</span>`;
        }

        // Assignment reveal
        const assignmentCard = document.getElementById("assignmentContainer");
        if (assignment) {
            document.getElementById("assignmentRecipientName").textContent = assignment.recipient_username;
            document.getElementById("assignmentRecipientWishlist").textContent = assignment.recipient_wishlist;
            assignmentCard.style.display = "block";
        } else {
            assignmentCard.style.display = "none";
        }

        // Shuffle controls
        const shuffleStatusBox = document.getElementById("shuffleStatusBox");
        const btnShuffle = document.getElementById("btnShuffle");
        
        if (group.is_shuffled) {
            shuffleStatusBox.innerHTML = `
                <div style="color: #15803d; font-weight: 700;">✅ Secret Santas have been assigned!</div>
                <div style="font-size: 0.85rem; color: #64748b; margin-top: 4px;">Each member can see who they are gifting to above. You can re-shuffle anytime if new members join.</div>
            `;
            btnShuffle.innerHTML = "<span>🔄 Re-Shuffle Secret Santas</span>";
        } else {
            shuffleStatusBox.innerHTML = `
                <div>Currently <strong>${members.length}</strong> member${members.length !== 1 ? 's' : ''} in the group.</div>
                <div style="font-size: 0.85rem; color: #64748b; margin-top: 4px;">Once all members have entered the code and joined, click Shuffle below!</div>
            `;
            btnShuffle.innerHTML = "<span>✨ Shuffle & Assign Secret Santas 🎅</span>";
        }

        // Members list
        document.getElementById("memberCountBadge").textContent = members.length;
        const membersGrid = document.getElementById("membersContainer");
        membersGrid.innerHTML = "";

        members.forEach(member => {
            const isMe = currentUser && (member.username.toLowerCase() === currentUser.username.toLowerCase());
            const chip = document.createElement("div");
            chip.className = "member-chip";

            chip.innerHTML = `
                <div class="member-chip-header">
                    <span class="member-chip-name">
                        ${isMe ? '⭐ ' : '🎅 '}${escapeHtml(member.username)} ${isMe ? '(You)' : ''}
                    </span>
                    ${member.is_creator ? '<span class="badge-creator">Creator</span>' : ''}
                </div>
                <div class="member-wishlist-preview">
                    <strong>Wishlist:</strong><br>
                    ${member.wishlist ? escapeHtml(member.wishlist) : '<em style="color:#9ca3af;">No wishlist yet</em>'}
                </div>
            `;
            membersGrid.appendChild(chip);
        });

    } catch (err) {
        // Navigates back if forbidden/not found
        navigate("dashboard");
    }
}

function refreshCurrentGroup() {
    if (currentGroupId) {
        loadGroupDetails(currentGroupId);
        showToast("Group refreshed! ❄️", "success");
    }
}

async function handleSaveWishlist(e) {
    e.preventDefault();
    if (!currentGroupId) return;

    const wishlistText = document.getElementById("myWishlistInput").value.trim();

    try {
        const res = await apiRequest(`/api/groups/${currentGroupId}/wishlist`, "PUT", { wishlist: wishlistText });
        showToast(res.message || "Wishlist saved! 🎁", "success");
        // Reload to update member preview
        loadGroupDetails(currentGroupId);
    } catch (err) {
        // Handled in apiRequest
    }
}

async function triggerShuffle() {
    if (!currentGroupId) return;

    const confirmed = confirm(
        "🎅 Are you ready to shuffle Secret Santas?\n\nThis will randomly assign each member a gift recipient. Nobody will be assigned to themselves!"
    );
    if (!confirmed) return;

    try {
        const res = await apiRequest(`/api/groups/${currentGroupId}/shuffle`, "POST");
        showToast(res.message || "Secret Santas assigned! 🎁", "success");
        loadGroupDetails(currentGroupId);
    } catch (err) {
        // Handled in apiRequest
    }
}

function copyGroupCode() {
    const code = document.getElementById("groupDetailCode").textContent.trim();
    if (!code || code === "------") return;

    navigator.clipboard.writeText(code).then(() => {
        showToast(`Copied code "${code}" to clipboard! 📋`, "success");
    }).catch(() => {
        showToast(`Invite Code: ${code}`, "success");
    });
}

// ================= UTILITIES & SNOWFLAKES =================

function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.innerText = str;
    return div.innerHTML;
}

function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const icon = type === "success" ? "🎁" : type === "error" ? "⚠️" : "🔔";
    toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(50px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function initSnowflakes() {
    const container = document.getElementById("snowflakes");
    if (!container) return;

    const flakeCount = 35;
    const flakeSymbols = ["❄", "❅", "❆", "•"];

    for (let i = 0; i < flakeCount; i++) {
        const flake = document.createElement("div");
        flake.className = "snowflake";
        flake.textContent = flakeSymbols[Math.floor(Math.random() * flakeSymbols.length)];
        
        flake.style.left = `${Math.random() * 100}vw`;
        flake.style.fontSize = `${Math.random() * 1.2 + 0.6}rem`;
        flake.style.opacity = `${Math.random() * 0.7 + 0.2}`;
        flake.style.animationDuration = `${Math.random() * 6 + 5}s`;
        flake.style.animationDelay = `${Math.random() * 5}s`;

        container.appendChild(flake);
    }
}

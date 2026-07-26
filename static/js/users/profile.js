(function (window, document) {
    const state = { overview: null, fullStudents: null, initialized: false };
    const el = (id) => document.getElementById(id);

    function setPageState(name, message = "") {
        el("profileLoading").hidden = name !== "loading";
        el("profileError").hidden = name !== "error";
        el("profileContent").hidden = name !== "content";
        if (message) el("profileErrorMessage").textContent = message;
    }

    function fillForm() {
        const user = state.overview.usuario;
        el("profileFormName").value = user.nome || "";
        el("profileFormEmail").value = user.email || "";
        el("profileFormRole").value = user.cargo || "";
        el("profileFormBirthDate").value = window.ProfileRenderers.formatDate(user.data_nascimento) || "Não informada";
        el("profileFormPassword").value = "";
        const feedback = el("profileFormFeedback");
        feedback.hidden = true;
        feedback.classList.remove("is-success");
    }

    function renderOverview(overview) {
        state.overview = overview;
        window.ProfileRenderers.renderIdentity(overview.usuario);
        fillForm();
        const teacher = Boolean(overview.teacher_dashboard);
        el("profileTeacherDashboard").hidden = !teacher;
        el("profileNonTeacher").hidden = teacher;
        if (teacher) window.ProfileRenderers.renderDashboard(overview.teacher_dashboard);
        setPageState("content");
    }

    async function loadOverview() {
        setPageState("loading");
        try {
            window.AppAuth.garantirToken();
            const overview = await window.AppApi.fetchJson("/me/profile/overview", {
                headers: window.AppAuth.criarHeadersAuth(),
            });
            renderOverview(overview);
        } catch (error) {
            if (error.status !== 401) {
                setPageState("error", error.message || "Tente novamente em alguns instantes.");
            }
        }
    }

    function setEditOpen(open) {
        const panel = el("profileEditPanel");
        const toggle = el("profileEditToggle");
        panel.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
        toggle.innerHTML = open
            ? '<i class="bi bi-x-lg" aria-hidden="true"></i> Fechar edição'
            : '<i class="bi bi-pencil" aria-hidden="true"></i> Editar perfil';
        if (open) {
            fillForm();
            el("profileFormName").focus();
        }
    }

    function showFormFeedback(message, success = false) {
        const feedback = el("profileFormFeedback");
        feedback.textContent = message;
        feedback.classList.toggle("is-success", success);
        feedback.hidden = false;
    }

    async function saveProfile(event) {
        event.preventDefault();
        const password = el("profileFormPassword").value;
        if (password && !window.AppAuth.validarSenhaForte(password)) {
            showFormFeedback("A senha deve ter ao menos 8 caracteres, com maiúscula, minúscula, número e caractere especial.");
            el("profileFormPassword").focus();
            return;
        }
        const submit = el("profileSubmit");
        submit.disabled = true;
        submit.textContent = "Salvando...";
        try {
            const updated = await window.AppApi.fetchJson("/me/profile", {
                method: "PATCH",
                headers: window.AppAuth.criarHeadersJsonAuth(),
                body: JSON.stringify({
                    nome: el("profileFormName").value.trim(),
                    email: el("profileFormEmail").value.trim(),
                    nova_senha: password,
                }),
            });
            Object.assign(state.overview.usuario, { nome: updated.nome, email: updated.email });
            window.ProfileRenderers.renderIdentity(state.overview.usuario);
            const cached = Object.assign({}, window.AppAuth.lerUsuarioCache() || {}, updated);
            window.AppAuth.salvarUsuarioCache(cached);
            window.AppNavbar?.aplicarUsuario?.(cached);
            el("profileFormPassword").value = "";
            showFormFeedback("Perfil atualizado com sucesso.", true);
        } catch (error) {
            showFormFeedback(error.message || "Não foi possível atualizar seu perfil.");
        } finally {
            submit.disabled = false;
            submit.textContent = "Salvar alterações";
        }
    }

    async function toggleStudents() {
        const button = el("profileStudentsToggle");
        const target = el("profileStudentsFull");
        if (!target.hidden) {
            target.hidden = true;
            button.textContent = "Ver todos";
            button.setAttribute("aria-expanded", "false");
            return;
        }
        button.disabled = true;
        button.textContent = "Carregando...";
        try {
            if (!state.fullStudents) {
                state.fullStudents = await window.AppApi.fetchJson("/me/profile/students", {
                    headers: window.AppAuth.criarHeadersAuth(),
                });
            }
            window.ProfileRenderers.renderStudentFull(state.fullStudents.itens, target);
            target.hidden = false;
            button.textContent = "Recolher lista";
            button.setAttribute("aria-expanded", "true");
            target.focus?.();
        } catch (error) {
            button.textContent = "Tentar novamente";
            button.setAttribute("aria-expanded", "false");
        } finally {
            button.disabled = false;
        }
    }

    function bindEvents() {
        el("profileRetry").addEventListener("click", loadOverview);
        el("profileEditToggle").addEventListener("click", () =>
            setEditOpen(el("profileEditPanel").hidden)
        );
        el("profileEditCancel").addEventListener("click", () => {
            fillForm();
            setEditOpen(false);
            el("profileEditToggle").focus();
        });
        el("profileForm").addEventListener("submit", saveProfile);
        el("profileStudentsToggle").addEventListener("click", toggleStudents);
    }

    function init() {
        if (state.initialized) return;
        state.initialized = true;
        bindEvents();
        loadOverview();
    }

    document.readyState === "loading"
        ? document.addEventListener("DOMContentLoaded", init, { once: true })
        : init();
})(window, document);

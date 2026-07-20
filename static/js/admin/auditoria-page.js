async function inicializarAdminAuditoria() {
    try {
        await carregarUsuarioAtual();
        if (!usuarioEhAdmin) {
            window.location.href = "/admin/turmas";
            return;
        }
        registerAuditEvents();
        await loadAuditEvents();
    } catch (err) {
        const mensagem = el("auditMessage");
        if (mensagem) mensagem.innerText = err.message || "Falha ao carregar as atividades.";
    }
}

inicializarAdminAuditoria();

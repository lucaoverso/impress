let recursoEmEdicaoId = null;

function aplicarModoFormularioRecurso(edicao = false) {
    const titulo = el("tituloFormRecurso");
    const btnSalvar = el("btnSalvarRecurso");
    const btnCancelar = el("btnCancelarEdicaoRecurso");
    if (!titulo || !btnSalvar || !btnCancelar) return;

    titulo.innerText = edicao ? "Editar recurso" : "Cadastrar recurso";
    btnSalvar.innerText = edicao ? "Salvar alterações" : "Cadastrar recurso";
    btnCancelar.style.display = edicao ? "inline-block" : "none";
}

function atualizarPreviewImagemRecurso(caminhoImagem = "") {
    const preview = el("recursoImagemPreview");
    const input = el("recursoImagemCapa");
    if (!preview || !input) return;

    const caminho = String(caminhoImagem || "").trim();
    input.value = caminho;
    preview.hidden = !caminho;
    preview.style.backgroundImage = caminho
        ? `linear-gradient(180deg, rgba(15, 23, 42, 0.08), rgba(15, 23, 42, 0.55)), url("${caminho}")`
        : "";
    preview.innerHTML = caminho ? "<span>Prévia da capa</span>" : "";
}

function limparFormularioRecurso() {
    el("formRecurso")?.reset();
    if (el("recursoQuantidadeItens")) el("recursoQuantidadeItens").value = "1";
    atualizarPreviewImagemRecurso("");
    recursoEmEdicaoId = null;
    aplicarModoFormularioRecurso(false);
}

function iniciarEdicaoRecurso(recurso) {
    recursoEmEdicaoId = Number(recurso.id);
    el("recursoNome").value = recurso.nome || "";
    el("recursoTipo").value = recurso.tipo || "";
    el("recursoDescricao").value = recurso.descricao || "";
    el("recursoQuantidadeItens").value = String(recurso.quantidade_itens ?? 1);
    atualizarPreviewImagemRecurso(recurso.imagem_capa || "");
    aplicarModoFormularioRecurso(true);
    el("formRecurso").scrollIntoView({ behavior: "smooth", block: "center" });
}

async function carregarRecursos() {
    const recursos = await fetchJson("/admin/recursos/dados?incluir_inativos=true", { headers });
    const lista = el("listaRecursosAdmin");
    if (!lista) return;
    lista.innerHTML = "";

    recursos.forEach((recurso) => {
        const item = document.createElement("li");
        item.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = `${recurso.nome} (${recurso.tipo})`;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `${recurso.descricao || "Sem descrição"} | Quantidade: ${recurso.quantidade_itens ?? 1} | Status: ${recurso.ativo ? "Ativo" : "Inativo"} | ${recurso.imagem_capa ? "Com capa" : "Sem capa"}`;

        if (recurso.imagem_capa) {
            const preview = document.createElement("div");
            preview.className = "admin-resource-image-preview is-listing";
            preview.style.backgroundImage = `linear-gradient(180deg, rgba(15, 23, 42, 0.08), rgba(15, 23, 42, 0.55)), url("${recurso.imagem_capa}")`;
            preview.innerHTML = "<span>Capa atual</span>";
            item.appendChild(preview);
        }

        const quantidade = document.createElement("input");
        quantidade.type = "number";
        quantidade.min = "1";
        quantidade.value = String(recurso.quantidade_itens ?? 1);
        quantidade.title = "Quantidade de itens";

        const salvarQuantidade = document.createElement("button");
        salvarQuantidade.type = "button";
        salvarQuantidade.innerText = "Salvar quantidade";
        salvarQuantidade.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/recursos/${recurso.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        nome: recurso.nome,
                        tipo: recurso.tipo,
                        descricao: recurso.descricao || "",
                        quantidade_itens: Number(quantidade.value),
                        imagem_capa: recurso.imagem_capa || "",
                    }),
                });
                setMensagem("msgRecurso", `Quantidade atualizada para ${recurso.nome}.`);
                await carregarRecursos();
            } catch (err) {
                setMensagem("msgRecurso", err.message, true);
            }
        });

        const editar = document.createElement("button");
        editar.type = "button";
        editar.innerText = "Editar cadastro";
        editar.addEventListener("click", () => iniciarEdicaoRecurso(recurso));

        const status = document.createElement("button");
        status.type = "button";
        status.innerText = recurso.ativo ? "Desativar" : "Ativar";
        status.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/recursos/${recurso.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(recurso.ativo) }),
                });
                await carregarRecursos();
            } catch (err) {
                setMensagem("msgRecurso", err.message, true);
            }
        });

        const acoes = document.createElement("div");
        acoes.className = "admin-inline";
        acoes.append(quantidade, salvarQuantidade, editar, status);
        item.append(titulo, detalhe, acoes);
        lista.appendChild(item);
    });
}

async function uploadImagemRecurso() {
    const inputArquivo = el("recursoImagemArquivo");
    const arquivo = inputArquivo?.files?.[0];
    if (!arquivo) {
        setMensagem("msgRecurso", "Escolha uma imagem antes de enviar.", true);
        return;
    }

    const formData = new FormData();
    formData.append("arquivo", arquivo);
    try {
        const response = await fetch("/admin/recursos/upload-imagem", { method: "POST", headers, body: formData });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload?.detail || "Não foi possível enviar a imagem.");
        atualizarPreviewImagemRecurso(payload.imagem_capa || "");
        inputArquivo.value = "";
        setMensagem("msgRecurso", "Imagem enviada com sucesso.");
    } catch (err) {
        setMensagem("msgRecurso", err.message, true);
    }
}

function removerImagemRecursoSelecionada() {
    atualizarPreviewImagemRecurso("");
    if (el("recursoImagemArquivo")) el("recursoImagemArquivo").value = "";
}

async function cadastrarRecurso(event) {
    event.preventDefault();
    const payload = {
        nome: el("recursoNome").value.trim(),
        tipo: el("recursoTipo").value.trim(),
        descricao: el("recursoDescricao").value.trim(),
        quantidade_itens: Number(el("recursoQuantidadeItens").value),
        imagem_capa: el("recursoImagemCapa").value.trim(),
    };

    try {
        const url = recursoEmEdicaoId ? `/admin/recursos/${recursoEmEdicaoId}` : "/admin/recursos";
        await fetchJson(url, {
            method: recursoEmEdicaoId ? "PUT" : "POST",
            headers: headersJson,
            body: JSON.stringify(payload),
        });
        setMensagem("msgRecurso", recursoEmEdicaoId ? "Recurso atualizado com sucesso." : "Recurso cadastrado com sucesso.");
        limparFormularioRecurso();
        await carregarRecursos();
    } catch (err) {
        setMensagem("msgRecurso", err.message, true);
    }
}

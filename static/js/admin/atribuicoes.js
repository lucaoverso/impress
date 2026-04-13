async function carregarOpcoesProfessor() {
    const dados = await fetchJson("/admin/professores/opcoes", { headers });
    opcoesProfessor = {
        turmas: Array.isArray(dados.turmas) ? dados.turmas : [],
        disciplinas: Array.isArray(dados.disciplinas) ? dados.disciplinas : []
    };

    renderCheckboxes("profTurmasLista", opcoesProfessor.turmas, "turma");
    renderCheckboxes("profDisciplinasLista", opcoesProfessor.disciplinas, "disciplina");
}

async function carregarContextoAtribuicoesDocentes() {
    const dados = await fetchJson("/admin/atribuicoes-docentes/contexto", { headers });
    contextoAtribuicoesDocentes = {
        professores: Array.isArray(dados.professores) ? dados.professores : [],
        turmas: Array.isArray(dados.turmas) ? dados.turmas : [],
        disciplinas: Array.isArray(dados.disciplinas) ? dados.disciplinas : []
    };

    preencherSelectComItens(
        "atribuicaoProfessor",
        contextoAtribuicoesDocentes.professores,
        "Selecione o professor",
        { labelFn: (item) => item.label || item.nome || "" }
    );
    preencherSelectComItens(
        "atribuicaoDisciplina",
        contextoAtribuicoesDocentes.disciplinas,
        "Selecione a disciplina"
    );

    preencherSelectComItens(
        "filtroAtribuicaoProfessor",
        contextoAtribuicoesDocentes.professores,
        "Todos os professores",
        { permitirVazio: true, labelFn: (item) => item.label || item.nome || "" }
    );
    preencherSelectComItens(
        "filtroAtribuicaoTurma",
        contextoAtribuicoesDocentes.turmas,
        "Todas as turmas",
        { permitirVazio: true }
    );
    preencherSelectComItens(
        "filtroAtribuicaoDisciplina",
        contextoAtribuicoesDocentes.disciplinas,
        "Todas as disciplinas",
        { permitirVazio: true }
    );

    await carregarTurmasAtribuidasProfessorDisciplina();
}

function obterProfessorIdAtribuicaoFormulario() {
    return Number(el("atribuicaoProfessor")?.value || 0);
}

function obterDisciplinaIdAtribuicaoFormulario() {
    return Number(el("atribuicaoDisciplina")?.value || 0);
}

function obterTurmaIdsSelecionadasAtribuicao() {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return [];
    }
    return Array.from(container.querySelectorAll("input[type='checkbox']:checked"))
        .map((input) => Number(input.value))
        .filter((valor) => Number.isFinite(valor) && valor > 0);
}

function atualizarResumoTurmasAtribuicao() {
    const resumo = el("atribuicaoTurmasResumo");
    if (!resumo) {
        return;
    }

    const professorId = obterProfessorIdAtribuicaoFormulario();
    const disciplinaId = obterDisciplinaIdAtribuicaoFormulario();
    if (professorId <= 0 || disciplinaId <= 0) {
        resumo.innerText = "Selecione professor e disciplina para carregar as turmas.";
        return;
    }

    const selecionadas = obterTurmaIdsSelecionadasAtribuicao();
    if (selecionadas.length === 0) {
        resumo.innerText = "Nenhuma turma marcada. Salvar agora remove as atribuicoes desta disciplina para o professor.";
        return;
    }

    resumo.innerText = `${selecionadas.length} turma(s) marcada(s) para esta disciplina.`;
}

function renderTurmasAtribuicaoCheckboxes(turmaIdsSelecionadas = []) {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    if (!Array.isArray(contextoAtribuicoesDocentes.turmas) || contextoAtribuicoesDocentes.turmas.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma turma ativa cadastrada.";
        container.appendChild(vazio);
        atualizarResumoTurmasAtribuicao();
        return;
    }

    const selecionadas = new Set((turmaIdsSelecionadas || []).map((item) => String(item)));
    contextoAtribuicoesDocentes.turmas.forEach((turma, index) => {
        const label = document.createElement("label");
        label.className = "admin-checkbox-item admin-checkbox-item-stack";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.id = `atribuicao_turma_${index}_${turma.id}`;
        input.value = String(turma.id);
        input.checked = selecionadas.has(String(turma.id));
        input.addEventListener("change", atualizarResumoTurmasAtribuicao);

        const texto = document.createElement("span");
        texto.innerText = turma.nome;

        const detalhe = document.createElement("small");
        detalhe.className = "admin-checkbox-detail";
        detalhe.innerText = `Turno: ${nomeTurno(turma.turno)}`;

        const conteudo = document.createElement("div");
        conteudo.className = "admin-checkbox-content";
        conteudo.appendChild(texto);
        conteudo.appendChild(detalhe);

        label.appendChild(input);
        label.appendChild(conteudo);
        container.appendChild(label);
    });

    atualizarResumoTurmasAtribuicao();
}

async function carregarTurmasAtribuidasProfessorDisciplina() {
    const professorId = obterProfessorIdAtribuicaoFormulario();
    const disciplinaId = obterDisciplinaIdAtribuicaoFormulario();

    if (professorId <= 0 || disciplinaId <= 0) {
        renderTurmasAtribuicaoCheckboxes([]);
        return;
    }

    const lista = await fetchJson(
        `/admin/atribuicoes-docentes?professor_id=${professorId}&disciplina_id=${disciplinaId}`,
        { headers }
    );
    renderTurmasAtribuicaoCheckboxes(
        (Array.isArray(lista) ? lista : []).map((item) => Number(item.turma_id))
    );
}

function selecionarTodasTurmasAtribuicao() {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return;
    }
    Array.from(container.querySelectorAll("input[type='checkbox']")).forEach((input) => {
        input.checked = true;
    });
    atualizarResumoTurmasAtribuicao();
}

function limparSelecaoTurmasAtribuicao() {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return;
    }
    Array.from(container.querySelectorAll("input[type='checkbox']")).forEach((input) => {
        input.checked = false;
    });
    atualizarResumoTurmasAtribuicao();
}

function queryAtribuicoesDocentes() {
    const params = new URLSearchParams();
    const professorId = el("filtroAtribuicaoProfessor")?.value || "";
    const turmaId = el("filtroAtribuicaoTurma")?.value || "";
    const disciplinaId = el("filtroAtribuicaoDisciplina")?.value || "";
    if (professorId) params.set("professor_id", professorId);
    if (turmaId) params.set("turma_id", turmaId);
    if (disciplinaId) params.set("disciplina_id", disciplinaId);
    return params.toString() ? `?${params.toString()}` : "";
}

async function carregarAtribuicoesDocentes() {
    const lista = await fetchJson(`/admin/atribuicoes-docentes${queryAtribuicoesDocentes()}`, { headers });
    const ul = el("listaAtribuicoesDocentesAdmin");
    if (!ul) {
        return;
    }
    ul.innerHTML = "";

    if (!Array.isArray(lista) || lista.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma atribuição docente encontrada para os filtros selecionados.";
        ul.appendChild(vazio);
        return;
    }

    lista.forEach((item) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = `${item.professor_nome} | ${item.turma_nome} | ${item.disciplina_nome}`;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Turno: ${nomeTurno(item.turno)} | Status: ${
            item.professor_ativo && item.turma_ativa && item.disciplina_ativa ? "Ativo" : "Vínculo com item inativo"
        }`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.innerText = "Remover atribuição";
        btnExcluir.addEventListener("click", async () => {
            const confirmado = window.confirm(
                `Remover a atribuição de ${item.professor_nome} em ${item.disciplina_nome} para ${item.turma_nome}?`
            );
            if (!confirmado) {
                return;
            }
            try {
                await fetchJson(`/admin/atribuicoes-docentes/${item.id}`, {
                    method: "DELETE",
                    headers
                });
                setMensagem("msgAtribuicoesDocentes", "Atribuição docente removida com sucesso.");
                await Promise.all([
                    carregarProfessores(),
                    carregarContextoAtribuicoesDocentes(),
                    carregarAtribuicoesDocentes(),
                    atualizarEstruturaEscolarSePermitido()
                ]);
            } catch (err) {
                setMensagem("msgAtribuicoesDocentes", err.message, true);
            }
        });

        linha.appendChild(btnExcluir);
        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        ul.appendChild(li);
    });
}

async function cadastrarAtribuicaoDocente(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/atribuicoes-docentes", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                professor_id: Number(el("atribuicaoProfessor").value),
                turma_id: Number(el("atribuicaoTurma").value),
                disciplina_id: Number(el("atribuicaoDisciplina").value)
            })
        });
        setMensagem("msgAtribuicoesDocentes", "Atribuição docente cadastrada com sucesso.");
        el("formAtribuicaoDocente").reset();
        await Promise.all([
            carregarProfessores(),
            carregarContextoAtribuicoesDocentes(),
            carregarAtribuicoesDocentes(),
            atualizarEstruturaEscolarSePermitido()
        ]);
    } catch (err) {
        setMensagem("msgAtribuicoesDocentes", err.message, true);
    }
}

function limparFiltrosAtribuicoesDocentes() {
    if (el("filtroAtribuicaoProfessor")) el("filtroAtribuicaoProfessor").value = "";
    if (el("filtroAtribuicaoTurma")) el("filtroAtribuicaoTurma").value = "";
    if (el("filtroAtribuicaoDisciplina")) el("filtroAtribuicaoDisciplina").value = "";
    carregarAtribuicoesDocentes().catch((err) => {
        setMensagem("msgAtribuicoesDocentes", err.message, true);
    });
}

async function carregarAtribuicoesDocentes() {
    const lista = await fetchJson(`/admin/atribuicoes-docentes${queryAtribuicoesDocentes()}`, { headers });
    const ul = el("listaAtribuicoesDocentesAdmin");
    if (!ul) {
        return;
    }
    ul.innerHTML = "";

    if (!Array.isArray(lista) || lista.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma atribuicao docente encontrada para os filtros selecionados.";
        ul.appendChild(vazio);
        return;
    }

    const grupos = new Map();
    lista.forEach((item) => {
        const chave = `${item.professor_id}::${item.disciplina_id}`;
        if (!grupos.has(chave)) {
            grupos.set(chave, {
                professor_id: Number(item.professor_id),
                professor_nome: item.professor_nome,
                disciplina_id: Number(item.disciplina_id),
                disciplina_nome: item.disciplina_nome,
                professor_ativo: Boolean(item.professor_ativo),
                disciplina_ativa: Boolean(item.disciplina_ativa),
                turmas: []
            });
        }
        grupos.get(chave).turmas.push({
            id: Number(item.turma_id),
            nome: item.turma_nome,
            turno: item.turno,
            ativa: Boolean(item.turma_ativa)
        });
    });

    Array.from(grupos.values()).forEach((item) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = `${item.professor_nome} | ${item.disciplina_nome}`;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Turmas: ${item.turmas.map((turma) => `${turma.nome} (${nomeTurno(turma.turno)})`).join(", ")}`;

        const status = document.createElement("p");
        status.className = "booking-detail";
        status.innerText = `Status: ${
            item.professor_ativo && item.disciplina_ativa && item.turmas.every((turma) => turma.ativa)
                ? "Ativo"
                : "Vinculo com item inativo"
        }`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar turmas";
        btnEditar.addEventListener("click", async () => {
            el("atribuicaoProfessor").value = String(item.professor_id);
            el("atribuicaoDisciplina").value = String(item.disciplina_id);
            await carregarTurmasAtribuidasProfessorDisciplina();
            ativarAbaAdmin("atribuicoes");
            el("formAtribuicaoDocente").scrollIntoView({ behavior: "smooth", block: "start" });
        });

        const btnLimpar = document.createElement("button");
        btnLimpar.type = "button";
        btnLimpar.innerText = "Limpar turmas";
        btnLimpar.addEventListener("click", async () => {
            const confirmado = window.confirm(
                `Remover todas as turmas de ${item.professor_nome} em ${item.disciplina_nome}?`
            );
            if (!confirmado) {
                return;
            }
            try {
                await fetchJson("/admin/atribuicoes-docentes/lote", {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        professor_id: item.professor_id,
                        disciplina_id: item.disciplina_id,
                        turma_ids: []
                    })
                });
                setMensagem("msgAtribuicoesDocentes", "Atribuicoes removidas com sucesso.");
                await Promise.all([
                    carregarProfessores(),
                    carregarContextoAtribuicoesDocentes(),
                    carregarAtribuicoesDocentes(),
                    atualizarEstruturaEscolarSePermitido()
                ]);
            } catch (err) {
                setMensagem("msgAtribuicoesDocentes", err.message, true);
            }
        });

        linha.appendChild(btnEditar);
        linha.appendChild(btnLimpar);
        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(status);
        li.appendChild(linha);
        ul.appendChild(li);
    });
}

async function cadastrarAtribuicaoDocente(event) {
    event.preventDefault();
    const professorId = obterProfessorIdAtribuicaoFormulario();
    const disciplinaId = obterDisciplinaIdAtribuicaoFormulario();
    const turmaIds = obterTurmaIdsSelecionadasAtribuicao();

    if (professorId <= 0) {
        setMensagem("msgAtribuicoesDocentes", "Selecione o professor.", true);
        return;
    }
    if (disciplinaId <= 0) {
        setMensagem("msgAtribuicoesDocentes", "Selecione a disciplina.", true);
        return;
    }
    if (turmaIds.length === 0) {
        const confirmado = window.confirm(
            "Nenhuma turma foi marcada. Deseja remover todas as atribuicoes desta disciplina para o professor?"
        );
        if (!confirmado) {
            return;
        }
    }

    try {
        const resposta = await fetchJson("/admin/atribuicoes-docentes/lote", {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                professor_id: professorId,
                disciplina_id: disciplinaId,
                turma_ids: turmaIds
            })
        });
        setMensagem("msgAtribuicoesDocentes", resposta.mensagem || "Atribuicoes atualizadas com sucesso.");
        await Promise.all([
            carregarProfessores(),
            carregarAtribuicoesDocentes(),
            carregarTurmasAtribuidasProfessorDisciplina(),
            atualizarEstruturaEscolarSePermitido()
        ]);
    } catch (err) {
        setMensagem("msgAtribuicoesDocentes", err.message, true);
    }
}

async function importarAtribuicoesDocentesArquivo(event) {
    event.preventDefault();
    const arquivo = el("arquivoJsonAtribuicoesDocentes")?.files?.[0];
    if (!arquivo) {
        setMensagem("msgAtribuicoesDocentes", "Selecione um arquivo JSON para importar.", true);
        return;
    }

    const formData = new FormData();
    formData.append("arquivo", arquivo);

    try {
        const resposta = await fetchJson("/admin/atribuicoes-docentes/importar", {
            method: "POST",
            headers,
            body: formData
        });
        setMensagem("msgAtribuicoesDocentes", comporMensagemImportacao(resposta), houveFalhaImportacao(resposta));
        el("formImportarAtribuicoesDocentes").reset();
        await Promise.all([
            carregarProfessores(),
            carregarContextoAtribuicoesDocentes(),
            carregarAtribuicoesDocentes(),
            atualizarEstruturaEscolarSePermitido()
        ]);
    } catch (err) {
        setMensagem("msgAtribuicoesDocentes", err.message, true);
    }
}

function baixarModeloAtribuicoesJson() {
    baixarArquivoTexto("modelo_atribuicoes_docentes.json", MODELO_JSON_ATRIBUICOES_DOCENTES);
}


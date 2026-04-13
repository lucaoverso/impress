async function carregarContextoTurmasDisciplinas() {
    const dados = await fetchJson("/admin/turmas-disciplinas/contexto", { headers });
    contextoTurmasDisciplinas = {
        professores: Array.isArray(dados.professores) ? dados.professores : [],
        turmas: Array.isArray(dados.turmas) ? dados.turmas : [],
        disciplinas: Array.isArray(dados.disciplinas) ? dados.disciplinas : []
    };
}

function registrarTurmasDisciplinasExpandidas() {
    const container = el("listaTurmasDisciplinasAdmin");
    if (!container) {
        return;
    }
    turmasDisciplinasExpandidas.clear();
    Array.from(container.querySelectorAll("details[data-turma-id][open]")).forEach((item) => {
        const turmaId = String(item.dataset.turmaId || "").trim();
        if (turmaId) {
            turmasDisciplinasExpandidas.add(turmaId);
        }
    });
}

function disciplinaBasePorId(disciplinaId) {
    return (Array.isArray(contextoTurmasDisciplinas.disciplinas) ? contextoTurmasDisciplinas.disciplinas : [])
        .find((item) => Number(item.id) === Number(disciplinaId)) || null;
}

function construirSelectProfessorTurmaDisciplina(valorAtual = "", professorAtual = null) {
    const select = document.createElement("select");
    const vazio = document.createElement("option");
    vazio.value = "";
    vazio.innerText = "Sem professor";
    select.appendChild(vazio);

    const professores = Array.isArray(contextoTurmasDisciplinas.professores)
        ? [...contextoTurmasDisciplinas.professores]
        : [];
    const possuiAtual = professores.some((item) => Number(item.id) === Number(valorAtual));
    if (!possuiAtual && Number(valorAtual) > 0 && professorAtual) {
        professores.push({
            id: Number(valorAtual),
            nome: professorAtual.professor_nome || "Professor vinculado",
            label: professorAtual.professor_nome || "Professor vinculado"
        });
    }

    professores
        .sort((a, b) => String(a.nome || a.label || "").localeCompare(String(b.nome || b.label || ""), "pt-BR"))
        .forEach((professor) => {
            const option = document.createElement("option");
            option.value = String(professor.id);
            option.innerText = professor.label || professor.nome || "";
            select.appendChild(option);
        });

    select.value = valorAtual ? String(valorAtual) : "";
    return select;
}

function construirSelectDisciplinasTurma(itensTurma = []) {
    const select = document.createElement("select");
    const vazio = document.createElement("option");
    vazio.value = "";
    vazio.innerText = "Selecione uma disciplina";
    select.appendChild(vazio);

    const disciplinaIdsTurma = new Set((itensTurma || []).map((item) => Number(item.disciplina_id)));
    const disciplinas = (Array.isArray(contextoTurmasDisciplinas.disciplinas) ? contextoTurmasDisciplinas.disciplinas : [])
        .filter((disciplina) => !disciplinaIdsTurma.has(Number(disciplina.id)))
        .sort((a, b) => String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR"));

    disciplinas.forEach((disciplina) => {
        const option = document.createElement("option");
        option.value = String(disciplina.id);
        option.innerText = `${disciplina.nome} (${disciplina.aulas_semanais ?? 0}h base)`;
        select.appendChild(option);
    });
    return select;
}

async function salvarTurmaDisciplinaInline(item, cargaInput, professorSelect) {
    try {
        const resposta = await fetchJson(`/admin/turmas-disciplinas/${item.id}`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                carga_horaria: Number(cargaInput.value || 0),
                professor_id: professorSelect.value ? Number(professorSelect.value) : null
            })
        });
        const professorTexto = resposta.professor_nome
            ? ` com ${resposta.professor_nome}`
            : " sem professor vinculado";
        setMensagem("msgTurmaDisciplina", `${resposta.disciplina_nome} atualizada em ${resposta.turma_nome}${professorTexto}.`);
        await Promise.all([
            atualizarAtribuicoesDocentesSePermitido(),
            carregarProfessores(),
            carregarDisciplinasAdmin()
        ]);
    } catch (err) {
        setMensagem("msgTurmaDisciplina", err.message, true);
    }
}

async function removerTurmaDisciplinaInline(item) {
    const confirmado = window.confirm(
        `Remover ${item.disciplina_nome} da turma ${item.turma_nome}?`
    );
    if (!confirmado) {
        return;
    }

    try {
        await fetchJson(`/admin/turmas-disciplinas/${item.id}`, {
            method: "DELETE",
            headers
        });
        setMensagem("msgTurmaDisciplina", `Disciplina ${item.disciplina_nome} removida da turma ${item.turma_nome}.`);
        await Promise.all([
            atualizarAtribuicoesDocentesSePermitido(),
            carregarProfessores(),
            carregarDisciplinasAdmin()
        ]);
    } catch (err) {
        setMensagem("msgTurmaDisciplina", err.message, true);
    }
}

function criarTabelaTurmaDisciplina(itensTurma = []) {
    const wrapper = document.createElement("div");
    wrapper.className = "admin-table-wrap";

    const tabela = document.createElement("table");
    tabela.className = "admin-table";

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Disciplina", "Carga horária", "Professor vinculado", "Ações"].forEach((titulo) => {
        const th = document.createElement("th");
        th.innerText = titulo;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");
    itensTurma.forEach((item) => {
        const tr = document.createElement("tr");

        const tdDisciplina = document.createElement("td");
        const titulo = document.createElement("strong");
        titulo.innerText = item.disciplina_nome;
        const detalhe = document.createElement("div");
        detalhe.className = "admin-table-meta";
        detalhe.innerText = `Base: ${item.carga_horaria_padrao ?? 0}h | ${
            item.disciplina_ativa ? "Disciplina ativa" : "Disciplina inativa"
        }`;
        tdDisciplina.appendChild(titulo);
        tdDisciplina.appendChild(detalhe);

        const tdCarga = document.createElement("td");
        const inputCarga = document.createElement("input");
        inputCarga.type = "number";
        inputCarga.min = "0";
        inputCarga.value = String(item.carga_horaria ?? 0);
        inputCarga.title = "Carga horária da disciplina na turma";
        tdCarga.appendChild(inputCarga);

        const tdProfessor = document.createElement("td");
        const selectProfessor = construirSelectProfessorTurmaDisciplina(
            item.professor_id ? String(item.professor_id) : "",
            item
        );
        tdProfessor.appendChild(selectProfessor);
        if (item.professor_id && !item.professor_ativo) {
            const alerta = document.createElement("div");
            alerta.className = "admin-table-meta";
            alerta.innerText = "Professor inativo";
            tdProfessor.appendChild(alerta);
        }

        const tdAcoes = document.createElement("td");
        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "admin-inline";

        const btnSalvar = document.createElement("button");
        btnSalvar.type = "button";
        btnSalvar.innerText = "Salvar";
        btnSalvar.addEventListener("click", () => {
            salvarTurmaDisciplinaInline(item, inputCarga, selectProfessor);
        });

        const btnRemover = document.createElement("button");
        btnRemover.type = "button";
        btnRemover.innerText = "Remover";
        btnRemover.addEventListener("click", () => {
            removerTurmaDisciplinaInline(item);
        });

        linhaAcoes.appendChild(btnSalvar);
        linhaAcoes.appendChild(btnRemover);
        tdAcoes.appendChild(linhaAcoes);

        tr.appendChild(tdDisciplina);
        tr.appendChild(tdCarga);
        tr.appendChild(tdProfessor);
        tr.appendChild(tdAcoes);
        tbody.appendChild(tr);
    });
    tabela.appendChild(tbody);
    wrapper.appendChild(tabela);
    return wrapper;
}

function criarFormularioAdicionarDisciplinaTurma(turma, itensTurma = []) {
    const form = document.createElement("form");
    form.className = "admin-subform";

    const titulo = document.createElement("h3");
    titulo.innerText = "Adicionar disciplina nesta turma";

    const ajuda = document.createElement("p");
    ajuda.className = "booking-detail";
    ajuda.innerText = "Escolha uma disciplina do catálogo ou digite um novo nome para já cadastrar e vincular à turma.";

    const selectDisciplina = construirSelectDisciplinasTurma(itensTurma);
    const inputNovaDisciplina = document.createElement("input");
    inputNovaDisciplina.type = "text";
    inputNovaDisciplina.placeholder = "Nova disciplina (opcional)";

    const inputCarga = document.createElement("input");
    inputCarga.type = "number";
    inputCarga.min = "0";
    inputCarga.placeholder = "Carga horária da turma";
    inputCarga.value = "0";

    const selectProfessor = construirSelectProfessorTurmaDisciplina();

    selectDisciplina.addEventListener("change", () => {
        const disciplina = disciplinaBasePorId(selectDisciplina.value);
        if (disciplina && Number(inputCarga.value || 0) === 0) {
            inputCarga.value = String(disciplina.aulas_semanais ?? 0);
        }
    });

    form.appendChild(titulo);
    form.appendChild(ajuda);
    form.appendChild(selectDisciplina);
    form.appendChild(inputNovaDisciplina);
    form.appendChild(inputCarga);
    form.appendChild(selectProfessor);

    const linhaBotoes = document.createElement("div");
    linhaBotoes.className = "admin-inline";

    const btnAdicionar = document.createElement("button");
    btnAdicionar.type = "submit";
    btnAdicionar.className = "btn-destaque";
    btnAdicionar.innerText = "Adicionar disciplina";
    linhaBotoes.appendChild(btnAdicionar);
    form.appendChild(linhaBotoes);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
            const disciplinaId = Number(selectDisciplina.value || 0);
            const payload = {
                turma_id: Number(turma.id),
                disciplina_id: disciplinaId > 0 ? disciplinaId : null,
                disciplina_nome: disciplinaId > 0 ? "" : inputNovaDisciplina.value.trim(),
                carga_horaria: Number(inputCarga.value || 0),
                professor_id: selectProfessor.value ? Number(selectProfessor.value) : null
            };
            const resposta = await fetchJson("/admin/turmas-disciplinas", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagem("msgTurmaDisciplina", `${resposta.disciplina_nome} adicionada à turma ${resposta.turma_nome}.`);
            form.reset();
            inputCarga.value = "0";
            await Promise.all([
                atualizarAtribuicoesDocentesSePermitido(),
                carregarProfessores(),
                carregarDisciplinasAdmin()
            ]);
        } catch (err) {
            setMensagem("msgTurmaDisciplina", err.message, true);
        }
    });

    return form;
}

function criarPainelTurmaDisciplina(turma, itensTurma = []) {
    const details = document.createElement("details");
    details.className = "admin-accordion-item";
    details.dataset.turmaId = String(turma.id);
    details.open = turmasDisciplinasExpandidas.has(String(turma.id));
    details.addEventListener("toggle", () => {
        if (details.open) {
            turmasDisciplinasExpandidas.add(String(turma.id));
        } else {
            turmasDisciplinasExpandidas.delete(String(turma.id));
        }
    });

    const summary = document.createElement("summary");
    summary.className = "admin-accordion-summary";

    const resumoPrincipal = document.createElement("div");
    resumoPrincipal.className = "admin-accordion-title";

    const titulo = document.createElement("strong");
    titulo.innerText = turma.nome;
    const detalhe = document.createElement("span");
    detalhe.innerText = `${nomeTurno(turma.turno)} | ${turma.quantidade_estudantes ?? 0} estudantes | ${
        turma.ativo ? "Ativa" : "Inativa"
    }`;
    resumoPrincipal.appendChild(titulo);
    resumoPrincipal.appendChild(detalhe);

    const badge = document.createElement("span");
    badge.className = "admin-accordion-badge";
    badge.innerText = `${itensTurma.length} disciplina(s)`;

    summary.appendChild(resumoPrincipal);
    summary.appendChild(badge);
    details.appendChild(summary);

    const corpo = document.createElement("div");
    corpo.className = "admin-accordion-body";

    if (itensTurma.length > 0) {
        corpo.appendChild(criarTabelaTurmaDisciplina(itensTurma));
    } else {
        const vazio = document.createElement("p");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma disciplina vinculada a esta turma.";
        corpo.appendChild(vazio);
    }

    corpo.appendChild(criarFormularioAdicionarDisciplinaTurma(turma, itensTurma));
    details.appendChild(corpo);
    return details;
}

async function carregarTurmasDisciplinasAdmin() {
    const container = el("listaTurmasDisciplinasAdmin");
    if (!container) {
        return;
    }

    registrarTurmasDisciplinasExpandidas();
    const lista = await fetchJson("/admin/turmas-disciplinas?incluir_inativos=true", { headers });
    const turmas = Array.isArray(contextoTurmasDisciplinas.turmas) ? contextoTurmasDisciplinas.turmas : [];

    container.innerHTML = "";
    if (turmas.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma turma cadastrada para organizar disciplinas.";
        container.appendChild(vazio);
        return;
    }

    const itensPorTurma = new Map();
    (Array.isArray(lista) ? lista : []).forEach((item) => {
        const turmaId = Number(item.turma_id);
        if (!itensPorTurma.has(turmaId)) {
            itensPorTurma.set(turmaId, []);
        }
        itensPorTurma.get(turmaId).push(item);
    });

    turmas
        .slice()
        .sort((a, b) => String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR"))
        .forEach((turma) => {
            container.appendChild(
                criarPainelTurmaDisciplina(turma, itensPorTurma.get(Number(turma.id)) || [])
            );
        });
}

async function carregarTurmasAdmin() {
    const turmas = await fetchJson("/admin/turmas?incluir_inativas=true", { headers });
    const ul = el("listaTurmasAdmin");
    ul.innerHTML = "";

    if (!Array.isArray(turmas) || turmas.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma turma cadastrada.";
        ul.appendChild(vazio);
        return;
    }

    turmas.forEach((turma) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = turma.nome;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Turno: ${nomeTurno(turma.turno)} | Estudantes: ${turma.quantidade_estudantes ?? 0} | Status: ${turma.ativo ? "Ativa" : "Inativa"}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputTurno = document.createElement("select");
        ["MATUTINO", "VESPERTINO", "VESPERTINO_EM", "INTEGRAL"].forEach((turno) => {
            const option = document.createElement("option");
            option.value = turno;
            option.innerText = nomeTurno(turno);
            inputTurno.appendChild(option);
        });
        inputTurno.value = turma.turno && TURNO_LABEL[turma.turno] ? turma.turno : "MATUTINO";

        const inputQuantidade = document.createElement("input");
        inputQuantidade.type = "number";
        inputQuantidade.min = "0";
        inputQuantidade.value = String(turma.quantidade_estudantes ?? 0);
        inputQuantidade.title = "Quantidade de estudantes";

        const btnSalvarDados = document.createElement("button");
        btnSalvarDados.type = "button";
        btnSalvarDados.innerText = "Salvar dados";
        btnSalvarDados.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/turmas/${turma.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        turno: inputTurno.value,
                        quantidade_estudantes: Number(inputQuantidade.value)
                    })
                });
                setMensagem("msgTurma", `Dados da turma ${turma.nome} atualizados.`);
                await Promise.all([carregarTurmasAdmin(), atualizarAtribuicoesDocentesSePermitido()]);
            } catch (err) {
                setMensagem("msgTurma", err.message, true);
            }
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = turma.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/turmas/${turma.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(turma.ativo) })
                });
                await Promise.all([
                    carregarTurmasAdmin(),
                    atualizarOpcoesProfessorSePermitido(),
                    atualizarAtribuicoesDocentesSePermitido()
                ]);
            } catch (err) {
                setMensagem("msgTurma", err.message, true);
            }
        });

        linha.appendChild(inputTurno);
        linha.appendChild(inputQuantidade);
        linha.appendChild(btnSalvarDados);

        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        li.appendChild(btnStatus);
        ul.appendChild(li);
    });
}

async function cadastrarTurma(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/turmas", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                nome: el("turmaNome").value.trim(),
                turno: el("turmaTurno").value,
                quantidade_estudantes: Number(el("turmaQuantidadeEstudantes").value)
            })
        });

        setMensagem("msgTurma", "Turma cadastrada com sucesso.");
        el("formTurma").reset();
        el("turmaTurno").value = "MATUTINO";
        el("turmaQuantidadeEstudantes").value = "0";
        await Promise.all([
            carregarTurmasAdmin(),
            atualizarOpcoesProfessorSePermitido(),
            atualizarAtribuicoesDocentesSePermitido()
        ]);
    } catch (err) {
        setMensagem("msgTurma", err.message, true);
    }
}

async function carregarDisciplinasAdmin() {
    const disciplinas = await fetchJson("/admin/disciplinas?incluir_inativas=true", { headers });
    const ul = el("listaDisciplinasAdmin");
    ul.innerHTML = "";

    if (!Array.isArray(disciplinas) || disciplinas.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma disciplina cadastrada.";
        ul.appendChild(vazio);
        return;
    }

    disciplinas.forEach((disciplina) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = disciplina.nome;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Carga horaria base: ${disciplina.aulas_semanais ?? 0}h | Status: ${disciplina.ativo ? "Ativa" : "Inativa"}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputAulas = document.createElement("input");
        inputAulas.type = "number";
        inputAulas.min = "0";
        inputAulas.value = String(disciplina.aulas_semanais ?? 0);
        inputAulas.title = "Carga horaria base";

        const btnSalvarDados = document.createElement("button");
        btnSalvarDados.type = "button";
        btnSalvarDados.innerText = "Salvar carga";
        btnSalvarDados.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/disciplinas/${disciplina.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        aulas_semanais: Number(inputAulas.value)
                    })
                });
                setMensagem("msgDisciplina", `Carga horaria base da disciplina ${disciplina.nome} atualizada.`);
                await Promise.all([carregarDisciplinasAdmin(), atualizarAtribuicoesDocentesSePermitido()]);
            } catch (err) {
                setMensagem("msgDisciplina", err.message, true);
            }
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = disciplina.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/disciplinas/${disciplina.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(disciplina.ativo) })
                });
                await Promise.all([
                    carregarDisciplinasAdmin(),
                    atualizarOpcoesProfessorSePermitido(),
                    atualizarAtribuicoesDocentesSePermitido()
                ]);
            } catch (err) {
                setMensagem("msgDisciplina", err.message, true);
            }
        });

        linha.appendChild(inputAulas);
        linha.appendChild(btnSalvarDados);

        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        li.appendChild(btnStatus);
        ul.appendChild(li);
    });
}

async function cadastrarDisciplina(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/disciplinas", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                nome: el("disciplinaNome").value.trim(),
                aulas_semanais: Number(el("disciplinaAulasSemanais").value)
            })
        });

        setMensagem("msgDisciplina", "Disciplina cadastrada com sucesso.");
        el("formDisciplina").reset();
        el("disciplinaAulasSemanais").value = "0";
        await Promise.all([
            carregarDisciplinasAdmin(),
            atualizarOpcoesProfessorSePermitido(),
            atualizarAtribuicoesDocentesSePermitido()
        ]);
    } catch (err) {
        setMensagem("msgDisciplina", err.message, true);
    }
}


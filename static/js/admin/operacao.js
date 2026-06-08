function queryPeriodo(prefix = "") {
    const inicio = el(`${prefix}relDataInicio`) ? el(`${prefix}relDataInicio`).value : el("relDataInicio").value;
    const fim = el(`${prefix}relDataFim`) ? el(`${prefix}relDataFim`).value : el("relDataFim").value;

    const params = new URLSearchParams();
    if (inicio) params.set("data_inicio", inicio);
    if (fim) params.set("data_fim", fim);
    return params.toString() ? `?${params.toString()}` : "";
}

function queryHistorico() {
    const params = new URLSearchParams();
    const inicio = el("inicio").value;
    const fim = el("fim").value;
    if (inicio) params.set("data_inicio", inicio);
    if (fim) params.set("data_fim", fim);
    return params.toString() ? `?${params.toString()}` : "";
}

function renderResumoStatusImpressao(status) {
    const resumo = el("statusResumoImpressao");
    if (!resumo) {
        return;
    }

    const semPapel = Boolean(status?.sem_papel);
    const mensagem = String(status?.mensagem || "").trim();
    const atualizadoEm = String(status?.atualizado_em || "").trim();
    const atualizadoEmFormatado = atualizadoEm ? formatarDataHora(atualizadoEm) : "agora";

    resumo.className = semPapel
        ? "admin-status-box is-warning"
        : "admin-status-box is-ok";
    resumo.innerHTML = semPapel
        ? `<strong>Impressao bloqueada</strong><p>${mensagem || "Sem papel informado no painel administrativo."}</p><small>Atualizado em: ${atualizadoEmFormatado}</small>`
        : `<strong>Impressao liberada</strong><p>Nenhum bloqueio por falta de papel ativo no momento.</p><small>Atualizado em: ${atualizadoEmFormatado}</small>`;
}

async function carregarStatusImpressaoAdmin() {
    const status = await fetchJson("/admin/impressao/status", { headers });

    const checkbox = el("statusSemPapel");
    const inputMensagem = el("statusMensagemImpressao");

    if (checkbox) {
        checkbox.checked = Boolean(status?.sem_papel);
    }
    if (inputMensagem) {
        inputMensagem.value = String(status?.mensagem || "");
    }

    renderResumoStatusImpressao(status);
}

async function salvarStatusImpressao(event) {
    event.preventDefault();
    try {
        const semPapel = Boolean(el("statusSemPapel")?.checked);
        const mensagem = String(el("statusMensagemImpressao")?.value || "").trim();

        await fetchJson("/admin/impressao/status", {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                sem_papel: semPapel,
                mensagem,
            }),
        });

        setMensagem(
            "msgStatusImpressao",
            semPapel
                ? "Bloqueio de impressao por falta de papel salvo."
                : "Impressao liberada novamente."
        );
        await carregarStatusImpressaoAdmin();
    } catch (err) {
        setMensagem("msgStatusImpressao", err.message, true);
    }
}

async function carregarFilaAdmin() {
    const jobs = await fetchJson("/admin/fila", { headers });
    const ul = el("fila-admin");
    ul.innerHTML = "";

    jobs.forEach((job) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const descricao = document.createElement("p");  
        descricao.innerText = `${job.arquivo} | ${job.status} | ${job.paginas_totais ?? 0} páginas | ${job.professor ? `Professor: ${job.professor.nome}` : "Sem professor associado"}`

        const actions = document.createElement("div");
        actions.className = "admin-inline";

        const btnCancelar = document.createElement("button");
        btnCancelar.type = "button";
        btnCancelar.innerText = "Cancelar";
        btnCancelar.addEventListener("click", () => cancelarJob(job.id));

        const btnUrgente = document.createElement("button");
        btnUrgente.type = "button";
        btnUrgente.innerText = "Urgente";
        btnUrgente.addEventListener("click", () => prioridadeJob(job.id));

        actions.appendChild(btnCancelar);
        actions.appendChild(btnUrgente);
        li.appendChild(descricao);
        li.appendChild(actions);
        ul.appendChild(li);
    });
}

async function cancelarJob(jobId) {
    try {
        await fetchJson(`/jobs/${jobId}/cancelar`, {
            method: "POST",
            headers
        });
        await carregarFilaAdmin();
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

async function prioridadeJob(jobId) {
    try {
        await fetchJson(`/jobs/${jobId}/prioridade`, {
            method: "POST",
            headers
        });
        await carregarFilaAdmin();
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

async function buscarHistorico() {
    const jobs = await fetchJson(`/admin/historico${queryHistorico()}`, { headers });
    const ul = el("historico-admin");
    ul.innerHTML = "";

    jobs.forEach((job) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        li.innerText = `${job.criado_em} | ${job.arquivo} | ${job.paginas_totais ?? 0} páginas | ${job.usuario_nome || "Usuário não informado"}`;
        ul.appendChild(li);
    });
}

async function carregarProfessores() {
    const mes = el("mesReferenciaCota").value || mesAtualIso();
    const dados = await fetchJson(`/admin/professores?mes=${mes}`, { headers });

    if (dados.regras_cota) {
        el("cotaMensalEscola").value = dados.regras_cota.cota_mensal_escola ?? 0;
        el("cotaBase").value = dados.regras_cota.base_paginas ?? 0;
        el("cotaPorAula").value = dados.regras_cota.paginas_por_aula ?? 0;
        el("cotaPorTurma").value = dados.regras_cota.paginas_por_turma ?? 0;
    }

    const ul = el("listaProfessoresAdmin");
    ul.innerHTML = "";

    dados.professores.forEach((prof) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = prof.acesso_coordenacao
            ? `${prof.nome} (${prof.email}) | Professor com acesso à coordenação`
            : `${prof.nome} (${prof.email})`;

        const cadastro = document.createElement("p");
        cadastro.className = "booking-detail";
        cadastro.innerText = `Nascimento: ${formatarDataBr(prof.data_nascimento)} | Turmas operacionais: ${resumoLista(prof.turmas_operacionais || prof.turmas)} | Disciplinas operacionais: ${resumoLista(prof.disciplinas_operacionais || prof.disciplinas)}`;

        const meta = document.createElement("p");
        const limiteMes = prof.cota_mes ? prof.cota_mes.limite_paginas : "-";
        const usadasMes = prof.cota_mes ? prof.cota_mes.usadas_paginas : "-";
        meta.className = "booking-detail";
        meta.innerText = `Projetada: ${prof.cota_projetada} | Mês: ${usadasMes}/${limiteMes}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputAulas = document.createElement("input");
        inputAulas.type = "number";
        inputAulas.min = "0";
        inputAulas.value = String(prof.aulas_semanais ?? "");
        inputAulas.title = "Aulas semanais";
        inputAulas.placeholder = "Quantidade de aulas semanais";

        const inputTurmas = document.createElement("input");
        inputTurmas.type = "number";
        inputTurmas.min = "0";
        inputTurmas.placeholder = "Quantidade de turmas";
        inputTurmas.value = String(prof.turmas_quantidade ?? "");
        inputTurmas.title = "Quantidade de turmas";

        const btnSalvar = document.createElement("button");
        btnSalvar.type = "button";
        btnSalvar.innerText = "Salvar carga";
        btnSalvar.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/professores/${prof.id}/carga`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        aulas_semanais: Number(inputAulas.value),
                        turmas_quantidade: Number(inputTurmas.value)
                    })
                });
                setMensagem("msgProfessor", `Carga atualizada para ${prof.nome}.`);
                await carregarProfessores();
            } catch (err) {
                setMensagem("msgProfessor", err.message, true);
            }
        });

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar cadastro";
        btnEditar.addEventListener("click", () => {
            iniciarEdicaoProfessor(prof);
        });

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.innerText = "Excluir professor";
        btnExcluir.addEventListener("click", async () => {
            await excluirProfessor(prof);
        });

        const btnPromover = document.createElement("button");
        btnPromover.type = "button";
        btnPromover.innerText = "Tornar coordenador";
        btnPromover.addEventListener("click", async () => {
            await promoverProfessorParaCoordenador(prof);
        });

        const linhaSenha = document.createElement("div");
        linhaSenha.className = "admin-inline";

        const inputNovaSenha = document.createElement("input");
        inputNovaSenha.type = "password";
        inputNovaSenha.placeholder = "Nova senha";
        inputNovaSenha.autocomplete = "new-password";

        const inputConfirmacaoSenha = document.createElement("input");
        inputConfirmacaoSenha.type = "password";
        inputConfirmacaoSenha.placeholder = "Confirmar nova senha";
        inputConfirmacaoSenha.autocomplete = "new-password";

        const btnRedefinirSenha = document.createElement("button");
        btnRedefinirSenha.type = "button";
        btnRedefinirSenha.innerText = "Redefinir senha";
        btnRedefinirSenha.addEventListener("click", async () => {
            const novaSenha = inputNovaSenha.value.trim();
            const confirmacao = inputConfirmacaoSenha.value.trim();

            if (!novaSenha) {
                setMensagem("msgProfessor", "Informe a nova senha para redefinir.", true);
                return;
            }
            if (!validarSenhaForte(novaSenha)) {
                setMensagem("msgProfessor", "Nova senha fora do padrao de seguranca.", true);
                return;
            }
            if (novaSenha !== confirmacao) {
                setMensagem("msgProfessor", "A confirmacao da nova senha nao confere.", true);
                return;
            }

            try {
                await fetchJson(`/admin/professores/${prof.id}/senha`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ nova_senha: novaSenha })
                });
                inputNovaSenha.value = "";
                inputConfirmacaoSenha.value = "";
                setMensagem("msgProfessor", `Senha redefinida para ${prof.nome}.`);
            } catch (err) {
                setMensagem("msgProfessor", err.message, true);
            }
        });

        linha.appendChild(inputAulas);
        linha.appendChild(inputTurmas);
        linha.appendChild(btnSalvar);
        linha.appendChild(btnEditar);
        linha.appendChild(btnPromover);
        linha.appendChild(btnExcluir);

        linhaSenha.appendChild(inputNovaSenha);
        linhaSenha.appendChild(inputConfirmacaoSenha);
        linhaSenha.appendChild(btnRedefinirSenha);

        li.appendChild(titulo);
        li.appendChild(cadastro);
        li.appendChild(meta);
        li.appendChild(linha);
        li.appendChild(linhaSenha);
        ul.appendChild(li);
    });
}

async function carregarCoordenadores() {
    const ul = el("listaCoordenadoresAdmin");
    if (!ul || !usuarioEhAdmin) {
        return;
    }

    const coordenadores = await fetchJson("/admin/coordenadores", { headers });
    ul.innerHTML = "";

    if (!Array.isArray(coordenadores) || coordenadores.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhum coordenador cadastrado.";
        ul.appendChild(vazio);
        return;
    }

    coordenadores.forEach((coord) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        li.innerText = `${coord.nome} (${coord.email}) | Nascimento: ${formatarDataBr(coord.data_nascimento)}`;
        ul.appendChild(li);
    });
}

async function promoverProfessorParaCoordenador(professor) {
    const professorId = Number(professor?.id || 0);
    if (professorId <= 0) {
        setMensagem("msgProfessor", "Professor invalido para promocao.", true);
        return;
    }

    const nomeProfessor = String(professor?.nome || "este professor").trim() || "este professor";
    const confirmado = window.confirm(
        `Transformar ${nomeProfessor} em coordenador? Ele saira da lista de professores e passara a ter acesso de gestao.`
    );
    if (!confirmado) {
        return;
    }

    try {
        await fetchJson(`/admin/professores/${professorId}/promover-coordenador`, {
            method: "PUT",
            headers,
        });
        if (professorEmEdicaoId === professorId) {
            limparFormularioProfessor();
        }
        setMensagem("msgProfessor", `${nomeProfessor} promovido para coordenador com sucesso.`);
        await Promise.all([
            carregarProfessores(),
            carregarCoordenadores(),
            atualizarAtribuicoesDocentesSePermitido(),
        ]);
    } catch (err) {
        setMensagem("msgProfessor", err.message, true);
    }
}

async function cadastrarProfessor(event) {
    event.preventDefault();
    if (!usuarioEhAdmin) {
        setMensagem("msgProfessor", "Apenas administradores podem cadastrar usuários.", true);
        return;
    }

    const cargoSelecionado = String(el("profCargo").value || CARGO_PROFESSOR).toUpperCase();
    const ehCoordenador = cargoSelecionado === CARGO_COORDENADOR;
    const turmas = listarSelecionados("profTurmasLista");
    const disciplinas = listarSelecionados("profDisciplinasLista");

    if (!ehCoordenador && turmas.length === 0) {
        setMensagem("msgProfessor", "Selecione ao menos uma turma.", true);
        return;
    }
    if (!ehCoordenador && disciplinas.length === 0) {
        setMensagem("msgProfessor", "Selecione ao menos uma disciplina.", true);
        return;
    }

    const payloadBase = {
        nome: el("profNome").value.trim(),
        email: el("profEmail").value.trim(),
        data_nascimento: el("profDataNascimento").value,
        aulas_semanais: Number(el("profAulas").value),
        acesso_coordenacao: Boolean(el("profAcessoCoordenacao")?.checked),
        turmas,
        disciplinas
    };

    try {
        if (professorEmEdicaoId) {
            if (ehCoordenador) {
                setMensagem("msgProfessor", "A edição deste formulário é exclusiva para professor.", true);
                return;
            }
            await fetchJson(`/admin/professores/${professorEmEdicaoId}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payloadBase)
            });
            setMensagem("msgProfessor", "Professor atualizado com sucesso.");
        } else {
            const senha = el("profSenha").value.trim();
            if (!validarSenhaForte(senha)) {
                setMensagem("msgProfessor", "Senha fora do padrão de segurança.", true);
                return;
            }

            if (ehCoordenador) {
                await fetchJson("/admin/coordenadores", {
                    method: "POST",
                    headers: headersJson,
                    body: JSON.stringify({
                        nome: payloadBase.nome,
                        email: payloadBase.email,
                        senha,
                        data_nascimento: payloadBase.data_nascimento
                    })
                });
                setMensagem("msgProfessor", "Coordenador cadastrado com sucesso.");
            } else {
                await fetchJson("/admin/professores", {
                    method: "POST",
                    headers: headersJson,
                    body: JSON.stringify({
                        ...payloadBase,
                        senha
                    })
                });
                setMensagem("msgProfessor", "Professor cadastrado com sucesso.");
            }
        }

        limparFormularioProfessor();
        if (ehCoordenador) {
            await carregarCoordenadores();
        } else {
            await Promise.all([carregarProfessores(), atualizarAtribuicoesDocentesSePermitido()]);
        }
    } catch (err) {
        setMensagem("msgProfessor", err.message, true);
    }
}

async function salvarRegrasCota(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/cotas/regras", {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                cota_mensal_escola: Number(el("cotaMensalEscola").value),
                base_paginas: Number(el("cotaBase").value),
                paginas_por_aula: Number(el("cotaPorAula").value),
                paginas_por_turma: Number(el("cotaPorTurma").value)
            })
        });

        setMensagem("msgCotas", "Regras de cota atualizadas.");
        await carregarProfessores();
    } catch (err) {
        setMensagem("msgCotas", err.message, true);
    }
}

async function recalcularCotasMes() {
    try {
        const mes = el("mesReferenciaCota").value || mesAtualIso();
        await fetchJson(`/admin/cotas/recalcular?mes=${mes}`, {
            method: "POST",
            headers
        });
        setMensagem("msgCotas", `Cotas recalculadas para ${mes}.`);
        await carregarProfessores();
    } catch (err) {
        setMensagem("msgCotas", err.message, true);
    }
}

async function carregarRecursos() {
    const recursos = await fetchJson("/admin/recursos?incluir_inativos=true", { headers });
    const ul = el("listaRecursosAdmin");
    ul.innerHTML = "";

    recursos.forEach((recurso) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = `${recurso.nome} (${recurso.tipo})`;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `${recurso.descricao || "Sem descrição"} | Quantidade: ${recurso.quantidade_itens ?? 1} | Status: ${recurso.ativo ? "Ativo" : "Inativo"}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        detalhe.innerText = `${recurso.descricao || "Sem descrição"} | Quantidade: ${recurso.quantidade_itens ?? 1} | Status: ${recurso.ativo ? "Ativo" : "Inativo"} | ${recurso.imagem_capa ? "Com capa" : "Sem capa"}`;

        if (recurso.imagem_capa) {
            const preview = document.createElement("div");
            preview.className = "admin-resource-image-preview is-listing";
            preview.style.backgroundImage = `linear-gradient(180deg, rgba(15, 23, 42, 0.08), rgba(15, 23, 42, 0.55)), url("${recurso.imagem_capa}")`;
            preview.innerHTML = "<span>Capa atual</span>";
            li.appendChild(preview);
        }

        const inputQuantidadeItens = document.createElement("input");
        inputQuantidadeItens.type = "number";
        inputQuantidadeItens.min = "1";
        inputQuantidadeItens.value = String(recurso.quantidade_itens ?? 1);
        inputQuantidadeItens.title = "Quantidade de itens";

        const btnSalvarQuantidade = document.createElement("button");
        btnSalvarQuantidade.type = "button";
        btnSalvarQuantidade.innerText = "Salvar quantidade";
        btnSalvarQuantidade.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/recursos/${recurso.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        nome: recurso.nome,
                        tipo: recurso.tipo,
                        descricao: recurso.descricao || "",
                        quantidade_itens: Number(inputQuantidadeItens.value),
                        imagem_capa: recurso.imagem_capa || ""
                    })
                });
                setMensagem("msgRecurso", `Quantidade atualizada para ${recurso.nome}.`);
                await carregarRecursos();
            } catch (err) {
                setMensagem("msgRecurso", err.message, true);
            }
        });

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar cadastro";
        btnEditar.addEventListener("click", () => {
            iniciarEdicaoRecurso(recurso);
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = recurso.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/recursos/${recurso.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(recurso.ativo) })
                });
                await carregarRecursos();
            } catch (err) {
                setMensagem("msgRecurso", err.message, true);
            }
        });

        linha.appendChild(inputQuantidadeItens);
        linha.appendChild(btnSalvarQuantidade);
        linha.appendChild(btnEditar);

        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        li.appendChild(btnStatus);
        ul.appendChild(li);
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
        const response = await fetch("/admin/recursos/upload-imagem", {
            method: "POST",
            headers,
            body: formData
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload?.detail || payload?.mensagem || "Nao foi possivel enviar a imagem.");
        }

        atualizarPreviewImagemRecurso(payload.imagem_capa || "");
        inputArquivo.value = "";
        setMensagem("msgRecurso", "Imagem enviada com sucesso.");
    } catch (err) {
        setMensagem("msgRecurso", err.message, true);
    }
}

function removerImagemRecursoSelecionada() {
    atualizarPreviewImagemRecurso("");
    const inputArquivo = el("recursoImagemArquivo");
    if (inputArquivo) {
        inputArquivo.value = "";
    }
}

async function cadastrarRecurso(event) {
    event.preventDefault();
    const payload = {
        nome: el("recursoNome").value.trim(),
        tipo: el("recursoTipo").value.trim(),
        descricao: el("recursoDescricao").value.trim(),
        quantidade_itens: Number(el("recursoQuantidadeItens").value),
        imagem_capa: el("recursoImagemCapa").value.trim()
    };

    try {
        if (recursoEmEdicaoId) {
            await fetchJson(`/admin/recursos/${recursoEmEdicaoId}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagem("msgRecurso", "Recurso atualizado com sucesso.");
        } else {
            await fetchJson("/admin/recursos", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagem("msgRecurso", "Recurso cadastrado com sucesso.");
        }

        limparFormularioRecurso();
        await carregarRecursos();
    } catch (err) {
        setMensagem("msgRecurso", err.message, true);
    }
}

function renderListaRelatorio(id, itens, formatador, vazio = "Sem dados no período.") {
    const ul = el(id);
    ul.innerHTML = "";

    if (!itens || itens.length === 0) {
        const li = document.createElement("li");
        li.className = "booking-empty";
        li.innerText = vazio;
        ul.appendChild(li);
        return;
    }

    itens.forEach((item) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        li.innerText = formatador(item);
        ul.appendChild(li);
    });
}

async function carregarRelatorios() {
    try {
        const query = queryPeriodo();
        const relImpressao = await fetchJson(`/admin/relatorio/impressao${query}`, { headers });
        const relRecursos = await fetchJson(`/admin/relatorio/recursos${query}`, { headers });

        renderListaRelatorio(
            "relatorioImpressaoAdmin",
            relImpressao,
            (item) => `${item.nome}: ${item.total_jobs} job(s), ${item.total_paginas} páginas`
        );

        renderListaRelatorio(
            "relatorioRecursosAdmin",
            relRecursos.por_recurso,
            (item) => `${item.recurso_nome} (${item.recurso_tipo}): ${item.total_reservas} reservas, ${item.professores_distintos} professor(es)`
        );

        renderListaRelatorio(
            "relatorioRecursosProfessorAdmin",
            relRecursos.por_professor,
            (item) => `${item.nome}: ${item.total_reservas} reserva(s)`
        );

        setMensagem("msgRelatorios", "Relatórios atualizados.");
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

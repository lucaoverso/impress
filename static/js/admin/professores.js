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

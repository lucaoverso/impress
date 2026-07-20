async function carregarOpcoesProfessor() {
    const dados = await fetchJson("/admin/professores/opcoes", { headers });
    opcoesProfessor = {
        turmas: Array.isArray(dados.turmas) ? dados.turmas : [],
        disciplinas: Array.isArray(dados.disciplinas) ? dados.disciplinas : []
    };
    renderCheckboxes("profTurmasLista", opcoesProfessor.turmas, "turma");
    renderCheckboxes("profDisciplinasLista", opcoesProfessor.disciplinas, "disciplina");
}

async function carregarProfessores() {
    const mes = el("mesReferenciaCota").value || mesAtualIso();
    const dados = await fetchJson(`/admin/professores/dados?mes=${mes}`, { headers });

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

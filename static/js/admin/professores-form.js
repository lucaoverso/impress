function atualizarVisibilidadeCamposCargo() {
    const cargo = String(el("profCargo")?.value || CARGO_PROFESSOR).toUpperCase();
    const hint = el("profCargoHint");
    const wrapperAcessoCoordenacao = el("profAcessoCoordenacaoWrapper");
    if (!hint) {
        return;
    }
    const ehCoordenador = cargo === CARGO_COORDENADOR;
    hint.style.display = ehCoordenador ? "block" : "none";
    if (wrapperAcessoCoordenacao) {
        wrapperAcessoCoordenacao.style.display = ehCoordenador ? "none" : "flex";
    }
}

function atualizarHintSenha() {
    const senha = el("profSenha").value.trim();
    const hint = el("profSenhaHint");
    if (!senha) {
        hint.style.color = "#4b5563";
        return;
    }
    hint.style.color = validarSenhaForte(senha) ? "#0f766e" : "#b42318";
}

function renderCheckboxes(containerId, opcoes, prefixo) {
    const container = el(containerId);
    container.innerHTML = "";

    if (!Array.isArray(opcoes) || opcoes.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma opção ativa cadastrada.";
        container.appendChild(vazio);
        return;
    }

    opcoes.forEach((item, index) => {
        const id = `${prefixo}_${index}`;
        const label = document.createElement("label");
        label.className = "admin-checkbox-item";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.id = id;
        input.value = item;

        const texto = document.createElement("span");
        texto.innerText = item;

        label.appendChild(input);
        label.appendChild(texto);
        container.appendChild(label);
    });
}

function listarSelecionados(containerId) {
    return Array.from(el(containerId).querySelectorAll("input[type='checkbox']:checked"))
        .map((input) => input.value);
}

function definirSelecionados(containerId, valores = []) {
    const selecionados = new Set((valores || []).map((item) => String(item)));
    Array.from(el(containerId).querySelectorAll("input[type='checkbox']")).forEach((input) => {
        input.checked = selecionados.has(String(input.value));
    });
}

function resumoLista(lista, limite = 3) {
    if (!Array.isArray(lista) || lista.length === 0) return "Não informado";
    if (lista.length <= limite) return lista.join(", ");
    return `${lista.slice(0, limite).join(", ")} +${lista.length - limite}`;
}

function formatarDataBr(dataIso) {
    if (!dataIso) return "Não informada";
    const data = new Date(`${dataIso}T00:00:00`);
    if (Number.isNaN(data.getTime())) return dataIso;
    return data.toLocaleDateString("pt-BR");
}

function aplicarModoFormularioProfessor(edicao = false) {
    const titulo = el("tituloFormProfessor");
    const btnSalvar = el("btnSalvarProfessor");
    const btnCancelar = el("btnCancelarEdicaoProfessor");
    const inputSenha = el("profSenha");
    const hintSenha = el("profSenhaHint");
    const selectCargo = el("profCargo");

    if (edicao) {
        titulo.innerText = "Editar professor";
        btnSalvar.innerText = "Salvar alterações";
        btnCancelar.style.display = "inline-block";
        if (selectCargo) {
            selectCargo.value = CARGO_PROFESSOR;
            selectCargo.disabled = true;
        }
        inputSenha.value = "";
        inputSenha.required = false;
        inputSenha.disabled = true;
        inputSenha.placeholder = "Senha não alterada nesta edição";
        hintSenha.innerText = "Edição de cadastro: a senha não é alterada por este formulário.";
        hintSenha.style.color = "#4b5563";
        atualizarVisibilidadeCamposCargo();
        return;
    }

    const cargoSelecionado = String(selectCargo?.value || CARGO_PROFESSOR).toUpperCase();
    const ehCoordenador = cargoSelecionado === CARGO_COORDENADOR;
    titulo.innerText = ehCoordenador ? "Cadastrar coordenador" : "Cadastrar professor";
    btnSalvar.innerText = "Cadastrar";
    btnCancelar.style.display = "none";
    if (selectCargo) {
        selectCargo.disabled = false;
    }
    inputSenha.required = true;
    inputSenha.disabled = false;
    inputSenha.placeholder = "Senha inicial";
    hintSenha.innerText = ehCoordenador
        ? "Senha inicial do coordenador."
        : "Mínimo 8 caracteres com maiúscula, minúscula, número e caractere especial.";
    atualizarHintSenha();
    atualizarVisibilidadeCamposCargo();
}

function limparFormularioProfessor() {
    el("formProfessor").reset();
    el("profCargo").value = CARGO_PROFESSOR;
    el("profAulas").value = "0";
    el("profAcessoCoordenacao").checked = false;
    definirSelecionados("profTurmasLista", []);
    definirSelecionados("profDisciplinasLista", []);
    professorEmEdicaoId = null;
    aplicarModoFormularioProfessor(false);
}

function iniciarEdicaoProfessor(professor) {
    professorEmEdicaoId = Number(professor.id);
    el("profNome").value = professor.nome || "";
    el("profEmail").value = professor.email || "";
    el("profDataNascimento").value = professor.data_nascimento || "";
    el("profCargo").value = CARGO_PROFESSOR;
    el("profAulas").value = String(professor.aulas_semanais ?? 0);
    el("profAcessoCoordenacao").checked = Boolean(professor.acesso_coordenacao);
    definirSelecionados("profTurmasLista", professor.turmas || []);
    definirSelecionados("profDisciplinasLista", professor.disciplinas || []);
    aplicarModoFormularioProfessor(true);
    ativarAbaAdmin("professores");
    el("formProfessor").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function excluirProfessor(professor) {
    const professorId = Number(professor?.id || 0);
    if (professorId <= 0) {
        setMensagem("msgProfessor", "Professor invalido para exclusao.", true);
        return;
    }

    const nomeProfessor = String(professor?.nome || "este professor").trim() || "este professor";
    const confirmado = window.confirm(
        `Excluir ${nomeProfessor}? O acesso sera bloqueado e o professor saira das listas operacionais.`
    );
    if (!confirmado) {
        return;
    }

    try {
        await fetchJson(`/admin/professores/${professorId}`, {
            method: "DELETE",
            headers
        });
        if (professorEmEdicaoId === professorId) {
            limparFormularioProfessor();
        }
        setMensagem("msgProfessor", `${nomeProfessor} excluido com sucesso.`);
        await Promise.all([carregarProfessores(), atualizarAtribuicoesDocentesSePermitido()]);
    } catch (err) {
        setMensagem("msgProfessor", err.message, true);
    }
}

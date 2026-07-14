let configuracoesAulasAdmin = [];

const JANELA_AULAS_PADRAO_POR_TURNO = {
    MATUTINO: [1, 5],
    VESPERTINO: [6, 10],
    VESPERTINO_EM: [6, 11],
    INTEGRAL: [1, 9],
};

function tipoConfiguracaoAula(item = {}) {
    return String(item?.tipo || "AULA").trim().toUpperCase();
}

function configuracoesAulasAtivas() {
    return (Array.isArray(configuracoesAulasAdmin) ? configuracoesAulasAdmin : [])
        .filter((item) => Boolean(item?.ativo ?? true))
        .sort((a, b) => Number(a?.ordem_visual || 0) - Number(b?.ordem_visual || 0));
}

function aulasGlobaisConfiguradasAdmin() {
    return configuracoesAulasAtivas()
        .filter((item) => tipoConfiguracaoAula(item) === "AULA")
        .sort((a, b) => Number(a?.aula_numero || 0) - Number(b?.aula_numero || 0));
}

function obterConfiguracaoAulaAdminPorId(configuracaoId) {
    return configuracoesAulasAdmin.find((item) => Number(item.id) === Number(configuracaoId)) || null;
}

function rotuloCurtoAulaAdmin(item = {}) {
    if (String(item?.label_curta || "").trim()) return String(item.label_curta).trim();
    if (tipoConfiguracaoAula(item) === "AULA" && Number(item?.aula_numero || 0) > 0) {
        return `${Number(item.aula_numero)}a aula`;
    }
    return String(item?.nome || "Intervalo").trim() || "Intervalo";
}

function textoHorarioConfiguracaoAula(item = {}) {
    const inicio = String(item?.horario_inicio || "").trim();
    const fim = String(item?.horario_fim || "").trim();
    return inicio && fim ? `${inicio} - ${fim}` : "Horário não informado";
}

function preencherSelectAulasGlobais(select, aulas, valorAtual = 0, placeholder = "") {
    if (!select) return;
    select.innerHTML = "";
    if (placeholder) {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = placeholder;
        select.appendChild(option);
    }
    (aulas || []).forEach((aula) => {
        const option = document.createElement("option");
        option.value = String(Number(aula?.aula_numero || 0));
        option.innerText = rotuloCurtoAulaAdmin(aula);
        select.appendChild(option);
    });
    const valor = Number(valorAtual || 0);
    if (valor > 0) select.value = String(valor);
    else if (!placeholder && select.options.length > 0) select.selectedIndex = 0;
    else select.value = "";
}

function sincronizarSelectsJanelaAulasTurma({
    turno, selectInicial, selectFinal, aulaInicialAtual = 0, aulaFinalAtual = 0, forcarPadrao = false,
} = {}) {
    if (!selectInicial || !selectFinal) return;
    const aulas = aulasGlobaisConfiguradasAdmin();
    if (aulas.length === 0) {
        preencherSelectAulasGlobais(selectInicial, [], 0, "Cadastre a grade primeiro");
        preencherSelectAulasGlobais(selectFinal, [], 0, "Cadastre a grade primeiro");
        selectInicial.disabled = true;
        selectFinal.disabled = true;
        return;
    }
    selectInicial.disabled = false;
    selectFinal.disabled = false;
    const numeros = aulas.map((item) => Number(item.aula_numero || 0)).filter((item) => item > 0);
    const janela = JANELA_AULAS_PADRAO_POR_TURNO[String(turno || "").toUpperCase()] || [1, 5];
    let inicial = Number(aulaInicialAtual || selectInicial.value || 0);
    if (forcarPadrao || !numeros.includes(inicial)) inicial = numeros.includes(janela[0]) ? janela[0] : numeros[0];
    preencherSelectAulasGlobais(selectInicial, aulas, inicial);
    const finais = aulas.filter((item) => Number(item.aula_numero || 0) >= inicial);
    const numerosFinais = finais.map((item) => Number(item.aula_numero || 0));
    let final = Number(aulaFinalAtual || selectFinal.value || 0);
    if (forcarPadrao || !numerosFinais.includes(final)) {
        final = numerosFinais.includes(janela[1]) ? janela[1] : numerosFinais.at(-1);
    }
    preencherSelectAulasGlobais(selectFinal, finais, Math.max(inicial, final));
}

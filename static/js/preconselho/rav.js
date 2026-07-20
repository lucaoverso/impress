function construirParametrosRav() {
    const params = new URLSearchParams({
        periodo_id: String(el("preconselhoPeriodoRav").value || "")
    });
    const turmaId = String(el("preconselhoTurmaRav").value || "").trim();
    if (turmaId) params.set("turma_id", turmaId);
    return params;
}

function modoVisualizacaoRav() {
    const modo = String(el("preconselhoModoRav")?.value || "estudante");
    return ["estudante", "disciplina", "habilidade"].includes(modo) ? modo : "estudante";
}

function chaveHabilidadeRav(habilidade) {
    return String(habilidade?.id || habilidade?.codigo || habilidade?.descricao || "").trim();
}

function rotuloHabilidadeRav(habilidade) {
    return [habilidade?.codigo, habilidade?.descricao].filter(Boolean).join(" - ");
}

function adicionarUnicoPorChave(mapa, chave, valor) {
    const chaveLimpa = String(chave || "").trim();
    if (chaveLimpa && !mapa.has(chaveLimpa)) {
        mapa.set(chaveLimpa, valor);
    }
}

function formatarListaRav(valores, vazio = "Nao informado") {
    const itens = Array.from(valores || []).map((valor) => String(valor || "").trim()).filter(Boolean);
    return itens.length ? itens.join("; ") : vazio;
}

function habilidadesRegistroRav(item) {
    return Array.isArray(item?.rav_habilidades) ? item.rav_habilidades : [];
}

function contarHabilidadesUnicasRav(itens) {
    const habilidades = new Set();
    itens.forEach((item) => {
        habilidadesRegistroRav(item).forEach((habilidade) => {
            const chave = chaveHabilidadeRav(habilidade);
            if (chave) habilidades.add(chave);
        });
    });
    return habilidades.size;
}

function renderizarBlocoRav(titulo, meta, habilidades, acoes, professor) {
    const mostrarHabilidades = habilidades !== null;
    const habilidadesTexto = mostrarHabilidades ? formatarListaRav(habilidades, "Nenhuma habilidade selecionada.") : "";
    const acoesTexto = formatarListaRav(acoes, "");
    const professorTexto = formatarListaRav(professor, "Nao informado");
    return `
        <div class="preconselho-rav-group-block">
            <div class="preconselho-rav-group-title">
                <strong>${escaparHtml(titulo)}</strong>
                ${meta ? `<span>${escaparHtml(meta)}</span>` : ""}
            </div>
            ${mostrarHabilidades ? `<p class="pcpi-item-note">${escaparHtml(`Habilidades: ${habilidadesTexto}`)}</p>` : ""}
            ${acoesTexto ? `<p class="pcpi-item-note is-secondary">${escaparHtml(`Acoes: ${acoesTexto}`)}</p>` : ""}
            <p class="pcpi-item-note is-secondary">${escaparHtml(`Professor: ${professorTexto}`)}</p>
        </div>
    `;
}

function agruparRavPorEstudante(itens) {
    const grupos = new Map();
    itens.forEach((item) => {
        const estudanteId = String(item.estudante_id || item.estudante_nome || "");
        const grupo = grupos.get(estudanteId) || {
            nome: item.estudante_nome || "Estudante sem nome",
            turmas: new Map(),
            disciplinas: new Map()
        };
        adicionarUnicoPorChave(grupo.turmas, item.turma_id || item.turma_nome, item.turma_nome);

        const disciplinaId = String(item.disciplina_id || item.disciplina_nome || "");
        const disciplina = grupo.disciplinas.get(disciplinaId) || {
            nome: item.disciplina_nome || "Disciplina nao informada",
            habilidades: new Map(),
            acoes: new Map(),
            professores: new Map()
        };
        habilidadesRegistroRav(item).forEach((habilidade) => {
            adicionarUnicoPorChave(disciplina.habilidades, chaveHabilidadeRav(habilidade), rotuloHabilidadeRav(habilidade));
        });
        adicionarUnicoPorChave(disciplina.acoes, item.rav_acoes, item.rav_acoes);
        adicionarUnicoPorChave(disciplina.professores, item.professor_id || item.professor_nome, item.professor_nome);

        grupo.disciplinas.set(disciplinaId, disciplina);
        grupos.set(estudanteId, grupo);
    });
    return Array.from(grupos.values());
}

function agruparRavPorDisciplina(itens) {
    const grupos = new Map();
    itens.forEach((item) => {
        const disciplinaId = String(item.disciplina_id || item.disciplina_nome || "");
        const grupo = grupos.get(disciplinaId) || {
            nome: item.disciplina_nome || "Disciplina nao informada",
            estudantes: new Map()
        };
        const estudanteId = String(item.estudante_id || item.estudante_nome || "");
        const estudante = grupo.estudantes.get(estudanteId) || {
            nome: item.estudante_nome || "Estudante sem nome",
            turma: item.turma_nome || "",
            habilidades: new Map(),
            acoes: new Map(),
            professores: new Map()
        };
        habilidadesRegistroRav(item).forEach((habilidade) => {
            adicionarUnicoPorChave(estudante.habilidades, chaveHabilidadeRav(habilidade), rotuloHabilidadeRav(habilidade));
        });
        adicionarUnicoPorChave(estudante.acoes, item.rav_acoes, item.rav_acoes);
        adicionarUnicoPorChave(estudante.professores, item.professor_id || item.professor_nome, item.professor_nome);

        grupo.estudantes.set(estudanteId, estudante);
        grupos.set(disciplinaId, grupo);
    });
    return Array.from(grupos.values());
}

function agruparRavPorHabilidade(itens) {
    const grupos = new Map();
    itens.forEach((item) => {
        const habilidades = habilidadesRegistroRav(item);
        const habilidadesDoRegistro = habilidades.length ? habilidades : [{ id: "sem-habilidade", descricao: "Sem habilidade selecionada" }];
        habilidadesDoRegistro.forEach((habilidade) => {
            const chave = chaveHabilidadeRav(habilidade) || "sem-habilidade";
            const grupo = grupos.get(chave) || {
                nome: rotuloHabilidadeRav(habilidade) || "Sem habilidade selecionada",
                estudantes: new Map()
            };
            const estudanteId = `${item.estudante_id || item.estudante_nome || ""}-${item.disciplina_id || item.disciplina_nome || ""}`;
            const estudante = grupo.estudantes.get(estudanteId) || {
                nome: item.estudante_nome || "Estudante sem nome",
                disciplina: item.disciplina_nome || "Disciplina nao informada",
                turma: item.turma_nome || "",
                acoes: new Map(),
                professores: new Map()
            };
            adicionarUnicoPorChave(estudante.acoes, item.rav_acoes, item.rav_acoes);
            adicionarUnicoPorChave(estudante.professores, item.professor_id || item.professor_nome, item.professor_nome);
            grupo.estudantes.set(estudanteId, estudante);
            grupos.set(chave, grupo);
        });
    });
    return Array.from(grupos.values());
}

function renderizarRavPorEstudante(itens) {
    return agruparRavPorEstudante(itens).map((grupo) => {
        const disciplinas = Array.from(grupo.disciplinas.values());
        return `
            <li class="pcpi-item pcpi-item-manual">
                <div class="pcpi-checkbox-row">
                    <div class="pcpi-item-body">
                        <div class="pcpi-item-top">
                            <strong>${escaparHtml(grupo.nome)}</strong>
                            <div class="pcpi-tag-group">
                                <span class="pcpi-chip pcpi-chip-automatico">RAV</span>
                                <span class="pcpi-chip">${disciplinas.length} disciplina(s)</span>
                            </div>
                        </div>
                        <p class="pcpi-item-line">${escaparHtml(formatarListaRav(grupo.turmas.values(), "Turma nao informada"))}</p>
                        <div class="preconselho-rav-group-list">
                            ${disciplinas.map((disciplina) => renderizarBlocoRav(
                                disciplina.nome,
                                "",
                                disciplina.habilidades.values(),
                                disciplina.acoes.values(),
                                disciplina.professores.values()
                            )).join("")}
                        </div>
                    </div>
                </div>
            </li>
        `;
    }).join("");
}

function renderizarRavPorDisciplina(itens) {
    return agruparRavPorDisciplina(itens).map((grupo) => {
        const estudantes = Array.from(grupo.estudantes.values());
        return `
            <li class="pcpi-item pcpi-item-manual">
                <div class="pcpi-checkbox-row">
                    <div class="pcpi-item-body">
                        <div class="pcpi-item-top">
                            <strong>${escaparHtml(grupo.nome)}</strong>
                            <div class="pcpi-tag-group">
                                <span class="pcpi-chip pcpi-chip-automatico">RAV</span>
                                <span class="pcpi-chip">${estudantes.length} estudante(s)</span>
                            </div>
                        </div>
                        <div class="preconselho-rav-group-list">
                            ${estudantes.map((estudante) => renderizarBlocoRav(
                                estudante.nome,
                                estudante.turma,
                                estudante.habilidades.values(),
                                estudante.acoes.values(),
                                estudante.professores.values()
                            )).join("")}
                        </div>
                    </div>
                </div>
            </li>
        `;
    }).join("");
}

function renderizarRavPorHabilidade(itens) {
    return agruparRavPorHabilidade(itens).map((grupo) => {
        const estudantes = Array.from(grupo.estudantes.values());
        return `
            <li class="pcpi-item pcpi-item-manual">
                <div class="pcpi-checkbox-row">
                    <div class="pcpi-item-body">
                        <div class="pcpi-item-top">
                            <strong>${escaparHtml(grupo.nome)}</strong>
                            <div class="pcpi-tag-group">
                                <span class="pcpi-chip pcpi-chip-automatico">RAV</span>
                                <span class="pcpi-chip">${estudantes.length} ocorrencia(s)</span>
                            </div>
                        </div>
                        <div class="preconselho-rav-group-list">
                            ${estudantes.map((estudante) => renderizarBlocoRav(
                                estudante.nome,
                                [estudante.turma, estudante.disciplina].filter(Boolean).join(" | "),
                                null,
                                estudante.acoes.values(),
                                estudante.professores.values()
                            )).join("")}
                        </div>
                    </div>
                </div>
            </li>
        `;
    }).join("");
}

function renderizarRav() {
    const dados = estadoRav.dados;
    const lista = el("listaRavPreconselho");
    const turmaSelecionada = Array.from(el("preconselhoTurmaRav")?.options || [])
        .find((option) => option.value === String(el("preconselhoTurmaRav")?.value || ""));

    if (!dados) {
        el("preconselhoResumoRavEstudantes").textContent = "0";
        el("preconselhoResumoRavRegistros").textContent = "0";
        el("preconselhoResumoRavHabilidades").textContent = "0";
        el("preconselhoResumoRavTurma").textContent = turmaSelecionada?.textContent || "Todas";
        lista.innerHTML = criarEstadoVazio("Selecione um periodo para visualizar os estudantes em RAV.");
        return;
    }

    const itens = Array.isArray(dados.itens) ? dados.itens : [];
    el("preconselhoResumoRavEstudantes").textContent = String(Number(dados.total_estudantes || 0));
    el("preconselhoResumoRavRegistros").textContent = String(Number(dados.total_registros || 0));
    el("preconselhoResumoRavHabilidades").textContent = String(contarHabilidadesUnicasRav(itens));
    el("preconselhoResumoRavTurma").textContent = turmaSelecionada?.textContent || "Todas";

    if (itens.length === 0) {
        lista.innerHTML = criarEstadoVazio("Nenhum estudante em RAV para os filtros selecionados.");
        return;
    }

    const modo = modoVisualizacaoRav();
    if (modo === "disciplina") {
        lista.innerHTML = renderizarRavPorDisciplina(itens);
        return;
    }
    if (modo === "habilidade") {
        lista.innerHTML = renderizarRavPorHabilidade(itens);
        return;
    }
    lista.innerHTML = renderizarRavPorEstudante(itens);
}

async function carregarRav() {
    limparMensagem("msgPreconselhoRav");
    const periodoId = Number(el("preconselhoPeriodoRav").value || 0);
    if (!periodoId) {
        estadoRav.dados = null;
        renderizarRav();
        return;
    }

    try {
        const resposta = await fetchComAuth(`/preconselho/rav/turma?${construirParametrosRav().toString()}`, { headers });
        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel carregar a visualizacao de RAV."));
        }
        estadoRav.dados = await resposta.json();
        renderizarRav();
        definirMensagem("msgPreconselhoRav", "Visualizacao de RAV atualizada.");
    } catch (erro) {
        estadoRav.dados = null;
        renderizarRav();
        definirMensagem("msgPreconselhoRav", erro.message || "Nao foi possivel carregar a visualizacao de RAV.", true);
    }
}


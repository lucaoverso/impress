function normalizarTurnoId(turnoId) {
    return String(turnoId || "").trim().toUpperCase();
}

function aulaLabel(aula) {
    return `${aula}ª aula`;
}

function faixaGlobalPorTurnoEAula(turnoId, aulaTurno) {
    const turno = normalizarTurnoId(turnoId);
    const aula = Number(aulaTurno || 0);
    const offset = TURNO_OFFSET_FAIXA[turno] ?? 0;
    if (!Number.isFinite(aula) || aula <= 0) return 0;

    let faixaGlobal = aula + offset;
    if (turno === "INTEGRAL" && aula > 5) {
        faixaGlobal += 1;
    }
    return faixaGlobal;
}

function aulaTurnoPorFaixa(turnoId, faixaGlobal) {
    const turno = normalizarTurnoId(turnoId);
    const faixa = Number(faixaGlobal || 0);
    const offset = TURNO_OFFSET_FAIXA[turno] ?? 0;
    if (!Number.isFinite(faixa) || faixa <= 0) return 0;

    if (turno === "INTEGRAL") {
        if (faixa >= 1 && faixa <= 5) return faixa;
        if (faixa >= 7) return faixa - 1;
        return 0;
    }

    return faixa - offset;
}

function obterTurmaOpcaoPorId(turmaId) {
    const turmaIdNumero = Number(turmaId || 0);
    return (opcoesOcorrencias.turmas || []).find((item) => Number(item.id) === turmaIdNumero) || null;
}

function obterProfessorOpcaoPorId(professorId) {
    const professorIdNumero = Number(professorId || 0);
    return (opcoesOcorrencias.professores || []).find((item) => Number(item.id) === professorIdNumero) || null;
}

function popularSugestoesProfessores() {
    limparMapaSugestoes(mapaBuscaProfessores);
    (opcoesOcorrencias.professores || []).forEach((item) => registrarMapaSugestoes(mapaBuscaProfessores, item));
    ocultarSugestoes("listaProfessoresBusca");
}

function popularSugestoesDisciplinas() {
    limparMapaSugestoes(mapaBuscaDisciplinas);
    (opcoesOcorrencias.disciplinas || []).forEach((item) => registrarMapaSugestoes(mapaBuscaDisciplinas, item));
    ocultarSugestoes("listaDisciplinasBusca");
}

function popularSugestoesRegimento() {
    limparMapaSugestoes(mapaBuscaRegimento);
    (opcoesOcorrencias.regimento_itens || []).forEach((item) => registrarMapaSugestoes(mapaBuscaRegimento, item));
    ocultarSugestoes("listaRegimentoBusca");
}

function popularSugestoesLeisBaseLegal() {
    limparMapaSugestoes(mapaBuscaLeisBaseLegal);
    leisBaseLegalCache.forEach((item) => registrarMapaSugestoes(mapaBuscaLeisBaseLegal, item));
    ocultarSugestoes("listaLeisBaseLegal");
}

function popularSugestoesArtigosBaseLegal() {
    limparMapaSugestoes(mapaBuscaArtigosBaseLegal);
    artigosBaseLegalCache.forEach((item) => registrarMapaSugestoes(mapaBuscaArtigosBaseLegal, item));
    ocultarSugestoes("listaArtigosBaseLegal");
}

function popularSugestoesIncisosBaseLegal() {
    limparMapaSugestoes(mapaBuscaIncisosBaseLegal);
    incisosBaseLegalCache.forEach((item) => registrarMapaSugestoes(mapaBuscaIncisosBaseLegal, item));
    ocultarSugestoes("listaIncisosBaseLegal");
}

function obterItensDisponiveisRegimento() {
    const idsSelecionados = new Set(obterIdsRegimentoSelecionadosFormulario());
    return (opcoesOcorrencias.regimento_itens || []).filter((item) => {
        const id = Number(item?.id || 0);
        if (id <= 0 || idsSelecionados.has(id)) {
            return false;
        }
        return Boolean(item.ativo);
    });
}

function correspondeTextoRegimento(item, termo) {
    const termoNormalizado = String(termo || "").trim().toLowerCase();
    if (!termoNormalizado) return false;

    return [
        item?.artigo,
        item?.label,
        item?.descricao
    ].some((valor) => String(valor || "").trim().toLowerCase() === termoNormalizado);
}

function buscarItemRegimentoPorTexto(termo) {
    const texto = String(termo || "").trim();
    if (!texto) return null;

    const itensDisponiveis = obterItensDisponiveisRegimento();
    const itemExato = itensDisponiveis.find((candidato) => correspondeTextoRegimento(candidato, texto));
    if (itemExato) return itemExato;

    const itensFiltrados = filtrarSugestoesLocais(itensDisponiveis, texto, {
        limite: 2,
        campos: ["artigo", "descricao", "label"]
    });
    return itensFiltrados.length === 1 ? itensFiltrados[0] : null;
}

function selecionarSugestaoRegimento(item) {
    const id = Number(item?.id || 0);
    if (id <= 0) return;

    const proximosIds = normalizarIdsRegimento([
        ...obterIdsRegimentoSelecionadosFormulario(),
        id
    ]);
    renderSelecionadorRegimento(proximosIds);
    el("ocorrenciaBuscaRegimento").value = "";
    ocultarSugestoes("listaRegimentoBusca");
}

function aplicarSelecaoRegimentoPorTexto({ limparQuandoInvalido = false } = {}) {
    const input = el("ocorrenciaBuscaRegimento");
    const texto = input.value.trim();
    if (!texto) {
        ocultarSugestoes("listaRegimentoBusca");
        return;
    }

    const item = buscarItemRegimentoPorTexto(texto);
    if (item) {
        selecionarSugestaoRegimento(item);
        return;
    }

    if (limparQuandoInvalido) {
        input.value = "";
    }
    ocultarSugestoes("listaRegimentoBusca");
}

function sincronizarRegimentoPendenteAntesSalvar() {
    const input = el("ocorrenciaBuscaRegimento");
    const texto = String(input?.value || "").trim();
    if (!texto) return true;

    const item = buscarItemRegimentoPorTexto(texto);
    if (item) {
        selecionarSugestaoRegimento(item);
        return true;
    }

    setMensagemOcorrencias(
        "Selecione uma opcao da base legal na lista antes de salvar a ocorrencia.",
        true
    );
    input.focus();
    atualizarSugestoesRegimentoBusca(true);
    return false;
}

function atualizarSugestoesRegimentoBusca(forcar = false) {
    const termo = el("ocorrenciaBuscaRegimento").value.trim();
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaRegimentoBusca");
        return;
    }

    const itensDisponiveis = obterItensDisponiveisRegimento();
    const itens = filtrarSugestoesLocais(itensDisponiveis, termo, {
        limite: 12,
        campos: ["artigo", "descricao", "label"]
    });

    const totalAtivos = (opcoesOcorrencias.regimento_itens || []).filter((item) => Boolean(item?.ativo)).length;
    const textoVazio = totalAtivos === 0
        ? "Cadastre bases legais ativas para pesquisar."
        : itensDisponiveis.length === 0
            ? "Todas as bases legais ativas ja foram anexadas."
        : "Nenhuma base legal encontrada.";
    preencherDatalist("listaRegimentoBusca", mapaBuscaRegimento, itens, {
        onSelect: selecionarSugestaoRegimento,
        textoVazio
    });
}

function faixasDisponiveisTurma(turma) {
    if (!turma || !turma.turno_valido) return [];

    const faixasApi = Array.isArray(turma.faixas_disponiveis)
        ? turma.faixas_disponiveis.map((valor) => Number(valor)).filter((valor) => Number.isInteger(valor) && valor > 0)
        : [];
    if (faixasApi.length > 0) {
        return faixasApi;
    }

    const totalAulas = Number(turma.aulas || 0);
    const faixasCalculadas = [];
    for (let aula = 1; aula <= totalAulas; aula++) {
        const faixa = faixaGlobalPorTurnoEAula(turma.turno, aula);
        if (faixa > 0) {
            faixasCalculadas.push(faixa);
        }
    }
    return faixasCalculadas;
}

function resolverFaixaOcorrenciaParaTurma(turma, aulaValor) {
    const texto = String(aulaValor || "").trim();
    if (!texto) return 0;

    const numero = Number.parseInt(texto, 10);
    if (!Number.isInteger(numero) || numero <= 0) return 0;

    const faixasTurma = faixasDisponiveisTurma(turma);
    if (faixasTurma.includes(numero)) {
        return numero;
    }

    const totalAulas = Number(turma?.aulas || 0);
    if (Number.isInteger(totalAulas) && numero <= totalAulas) {
        const faixaCalculada = faixaGlobalPorTurnoEAula(turma.turno, numero);
        if (faixaCalculada > 0 && faixasTurma.includes(faixaCalculada)) {
            return faixaCalculada;
        }
    }

    return 0;
}

function formatarAulaOcorrencia(ocorrencia) {
    const turma = obterTurmaOpcaoPorId(ocorrencia?.turma_id);
    const faixa = resolverFaixaOcorrenciaParaTurma(turma, ocorrencia?.aula);
    if (faixa <= 0 || !turma) {
        return ocorrencia?.aula || "Nao informada";
    }

    const aulaTurno = aulaTurnoPorFaixa(turma.turno, faixa);
    if (aulaTurno <= 0) {
        return `Faixa ${faixa}`;
    }
    return `${aulaLabel(aulaTurno)} (faixa ${faixa})`;
}

function obterOcorrenciaEmEdicaoAtual() {
    if (!ocorrenciaEmEdicaoId) return null;
    return (ocorrenciasCache || []).find((ocorrencia) => Number(ocorrencia.id) === Number(ocorrenciaEmEdicaoId)) || null;
}

function obterTextoOuPadrao(valor, padrao = "Nao informado") {
    const texto = String(valor || "").trim();
    return texto || padrao;
}

function obterEditorDescricao() {
    return el("ocorrenciaDescricaoEditor");
}

function normalizarCorFundoDescricao(valor) {
    const texto = String(valor || "").trim();
    if (!texto) return "";

    const hex = texto.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (hex) {
        const cor = hex[1].length === 3
            ? hex[1].split("").map((caractere) => caractere + caractere).join("")
            : hex[1];
        return `#${cor.toLowerCase()}`;
    }

    const rgb = texto.match(/^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\)$/i);
    if (!rgb) return "";
    const componentes = rgb.slice(1, 4).map((item) => Number(item));
    if (componentes.some((item) => !Number.isInteger(item) || item < 0 || item > 255)) {
        return "";
    }
    return `#${componentes.map((item) => item.toString(16).padStart(2, "0")).join("")}`;
}

function obterCorFundoElementoDescricao(elemento) {
    if (!elemento || !elemento.style) return "";
    return normalizarCorFundoDescricao(elemento.style.backgroundColor);
}

function criarFragmentoDescricaoComFilhos(node, elementoDestino) {
    node.childNodes.forEach((filho) => {
        elementoDestino.appendChild(sanitizarNoDescricao(filho));
    });
    return elementoDestino;
}

function sanitizarNoDescricao(node) {
    if (node.nodeType === Node.TEXT_NODE) {
        return document.createTextNode(node.textContent || "");
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
        return document.createDocumentFragment();
    }

    const tag = node.tagName.toLowerCase();
    if (tag === "script" || tag === "style") {
        return document.createDocumentFragment();
    }

    if (tag === "br") {
        return document.createElement("br");
    }

    if (tag === "b" || tag === "strong") {
        return criarFragmentoDescricaoComFilhos(node, document.createElement("strong"));
    }

    if (tag === "i" || tag === "em") {
        return criarFragmentoDescricaoComFilhos(node, document.createElement("em"));
    }

    if (tag === "mark") {
        const mark = document.createElement("mark");
        mark.style.backgroundColor = obterCorFundoElementoDescricao(node) || "#fff3a3";
        return criarFragmentoDescricaoComFilhos(node, mark);
    }

    if (tag === "span") {
        const cor = obterCorFundoElementoDescricao(node);
        if (cor) {
            const span = document.createElement("span");
            span.style.backgroundColor = cor;
            return criarFragmentoDescricaoComFilhos(node, span);
        }
    }

    if (tag === "div" || tag === "p") {
        return criarFragmentoDescricaoComFilhos(node, document.createElement("p"));
    }

    const fragmento = document.createDocumentFragment();
    node.childNodes.forEach((filho) => {
        fragmento.appendChild(sanitizarNoDescricao(filho));
    });
    return fragmento;
}

function sanitizarHtmlDescricao(html) {
    const template = document.createElement("template");
    template.innerHTML = String(html || "");

    const container = document.createElement("div");
    template.content.childNodes.forEach((node) => {
        container.appendChild(sanitizarNoDescricao(node));
    });
    return container.innerHTML.trim();
}

function obterTextoDescricaoEditor() {
    const editor = obterEditorDescricao();
    return String(editor?.innerText || "")
        .replace(/\u00a0/g, " ")
        .replace(/\n{3,}/g, "\n\n")
        .trim();
}

function sincronizarDescricaoEditor() {
    const editor = obterEditorDescricao();
    const textarea = el("ocorrenciaDescricao");
    const hiddenFormatado = el("ocorrenciaDescricaoFormatada");
    if (!editor || !textarea || !hiddenFormatado) return;

    const texto = obterTextoDescricaoEditor();
    const html = texto ? sanitizarHtmlDescricao(editor.innerHTML) : "";
    textarea.value = texto;
    hiddenFormatado.value = html;
}

function definirDescricaoEditor({ texto = "", html = "" } = {}) {
    const editor = obterEditorDescricao();
    if (!editor) return;

    const htmlSeguro = sanitizarHtmlDescricao(html);
    if (htmlSeguro) {
        editor.innerHTML = htmlSeguro;
    } else {
        editor.innerText = String(texto || "");
    }
    sincronizarDescricaoEditor();
}

function renderizarDescricaoFormatada(container, html, texto, fallback) {
    if (!container) return;
    const textoLimpo = obterTextoOuPadrao(texto, fallback);
    const htmlSeguro = String(texto || "").trim() ? sanitizarHtmlDescricao(html) : "";
    container.innerHTML = "";
    if (htmlSeguro) {
        container.innerHTML = htmlSeguro;
        return;
    }
    container.innerText = textoLimpo;
}

function selecaoPertenceAoEditorDescricao(range) {
    const editor = obterEditorDescricao();
    if (!editor || !range) return false;
    const ancestral = range.commonAncestorContainer;
    return ancestral === editor || editor.contains(ancestral);
}

function salvarSelecaoDescricaoEditor() {
    const selecao = window.getSelection();
    if (!selecao || selecao.rangeCount === 0) return;
    const range = selecao.getRangeAt(0);
    if (selecaoPertenceAoEditorDescricao(range)) {
        selecaoDescricaoEditor = range.cloneRange();
    }
}

function restaurarSelecaoDescricaoEditor() {
    const editor = obterEditorDescricao();
    if (!editor) return;
    const selecao = window.getSelection();
    if (!selecao) return;

    selecao.removeAllRanges();
    if (selecaoDescricaoEditor && selecaoPertenceAoEditorDescricao(selecaoDescricaoEditor)) {
        selecao.addRange(selecaoDescricaoEditor);
        return;
    }

    const range = document.createRange();
    range.selectNodeContents(editor);
    range.collapse(false);
    selecao.addRange(range);
}

function aplicarComandoDescricao(command) {
    const editor = obterEditorDescricao();
    if (!editor) return;

    editor.focus();
    restaurarSelecaoDescricaoEditor();

    if (command === "bold") {
        document.execCommand("styleWithCSS", false, false);
        document.execCommand("bold", false);
    } else if (command === "italic") {
        document.execCommand("styleWithCSS", false, false);
        document.execCommand("italic", false);
    } else if (command === "highlight") {
        document.execCommand("styleWithCSS", false, true);
        const cor = normalizarCorFundoDescricao(el("ocorrenciaDescricaoCorFundo")?.value) || "#fff3a3";
        if (!document.execCommand("hiliteColor", false, cor)) {
            document.execCommand("backColor", false, cor);
        }
    } else if (command === "removeFormat") {
        document.execCommand("styleWithCSS", false, false);
        document.execCommand("removeFormat", false);
    }

    sincronizarDescricaoEditor();
    salvarSelecaoDescricaoEditor();
    atualizarPreviewOcorrencia();
}

function normalizarIdBaseLegal(valor) {
    const numero = Number(valor || 0);
    return Number.isInteger(numero) && numero > 0 ? numero : null;
}

function normalizarTextoChaveBaseLegal(valor) {
    return String(valor || "").trim().replace(/\s+/g, " ").toLowerCase();
}

function limparRotuloArtigoLegadoBaseLegal(rotulo) {
    let texto = String(rotulo || "").trim();
    if (!texto) return "";

    if (texto.includes(" - Art.")) {
        texto = `Art.${texto.split(" - Art.", 2)[1] || ""}`;
    }

    texto = texto.replace(/,?\s*alinea\s+[a-z]\b.*$/i, "");
    texto = texto.replace(/,?\s*inciso\s+[IVXLCDM]+\b.*$/i, "");
    texto = texto.replace(/\s*-\s*[IVXLCDM]+\b.*$/i, "");
    return texto.replace(/\s+/g, " ").replace(/^[\s,;-]+|[\s,;-]+$/g, "");
}

function formatarLinhaArtigoBaseLegal(numero, descricao, rotuloLegado = "") {
    const numeroLimpo = String(numero || "").trim().replace(/^art\.?\s*/i, "");
    const descricaoLimpa = String(descricao || "").trim();
    if (numeroLimpo) {
        const prefixo = `Art. ${numeroLimpo}.`;
        return descricaoLimpa ? `${prefixo} ${descricaoLimpa}` : prefixo;
    }

    const rotulo = String(rotuloLegado || "").trim();
    return rotulo || descricaoLimpa || "Sem artigo";
}

function formatarLinhaIncisoBaseLegal(numero, descricao) {
    const numeroLimpo = String(numero || "").trim();
    const descricaoLimpa = String(descricao || "").trim();
    if (numeroLimpo && descricaoLimpa) {
        return `${numeroLimpo} - ${descricaoLimpa}`;
    }
    return numeroLimpo || descricaoLimpa;
}

function formatarLinhaAlineaBaseLegal(identificador, descricao) {
    const identificadorLimpo = String(identificador || "").trim();
    const descricaoLimpa = String(descricao || "").trim();
    if (identificadorLimpo && descricaoLimpa) {
        return `${identificadorLimpo}) ${descricaoLimpa}`;
    }
    return identificadorLimpo || descricaoLimpa;
}

function normalizarItensBaseLegal(itens) {
    const regexArtigo = /Art\.?\s*([^\s,;:-]+(?:[-A-Za-z0-9.]+)?)/i;
    const regexInciso = /(?:inciso\s+([IVXLCDM]+)|-\s*([IVXLCDM]+)\b)/i;
    const regexAlinea = /alinea\s+([a-z])\b/i;

    return (Array.isArray(itens) ? itens : [])
        .map((item, indice) => {
            if (!item || typeof item !== "object") return null;

            const artigo = String(item.artigo || "").trim();
            const descricao = String(item.descricao || "").trim();
            if (!artigo && !descricao) return null;

            let leiNome = String(item.lei_nome || "").trim();
            let artigoNumero = String(item.artigo_numero || "").trim();
            let artigoDescricao = String(item.artigo_descricao || "").trim();
            let incisoNumero = String(item.inciso_numero || "").trim();
            let incisoDescricao = String(item.inciso_descricao || "").trim();
            let alineaIdentificador = String(item.alinea_identificador || "").trim();
            let alineaDescricao = String(item.alinea_descricao || "").trim();

            if (!leiNome && artigo.includes(" - Art.")) {
                leiNome = artigo.split(" - Art.", 2)[0].trim();
            }

            if (!artigoNumero) {
                const matchArtigo = artigo.match(regexArtigo);
                if (matchArtigo?.[1]) {
                    artigoNumero = String(matchArtigo[1]).trim();
                }
            }

            if (!incisoNumero) {
                const matchInciso = artigo.match(regexInciso);
                if (matchInciso?.[1] || matchInciso?.[2]) {
                    incisoNumero = String(matchInciso[1] || matchInciso[2] || "").trim();
                }
            }

            if (!alineaIdentificador) {
                const matchAlinea = artigo.match(regexAlinea);
                if (matchAlinea?.[1]) {
                    alineaIdentificador = String(matchAlinea[1]).trim();
                }
            }

            let tipo = String(item.tipo || "").trim().toLowerCase();
            if (!tipo) {
                if (alineaIdentificador || normalizarIdBaseLegal(item.alinea_id)) {
                    tipo = "alinea";
                } else if (incisoNumero || normalizarIdBaseLegal(item.inciso_id)) {
                    tipo = "inciso";
                } else {
                    tipo = "artigo";
                }
            }

            if (tipo === "artigo" && !artigoDescricao) artigoDescricao = descricao;
            if (tipo === "inciso" && !incisoDescricao) incisoDescricao = descricao;
            if (tipo === "alinea" && !alineaDescricao) alineaDescricao = descricao;

            const ordemBruta = Number(item.ordem);
            const ordem = Number.isFinite(ordemBruta) && ordemBruta > 0
                ? Math.trunc(ordemBruta)
                : indice + 1;

            return {
                tipo,
                artigo_id: normalizarIdBaseLegal(item.artigo_id),
                inciso_id: normalizarIdBaseLegal(item.inciso_id),
                alinea_id: normalizarIdBaseLegal(item.alinea_id),
                lei_nome: leiNome || "",
                artigo_numero: artigoNumero || "",
                artigo_descricao: artigoDescricao || "",
                inciso_numero: incisoNumero || "",
                inciso_descricao: incisoDescricao || "",
                alinea_identificador: alineaIdentificador || "",
                alinea_descricao: alineaDescricao || "",
                artigo: artigo || "Sem artigo",
                descricao,
                ordem
            };
        })
        .filter(Boolean)
        .sort((a, b) => (
            a.ordem - b.ordem
            || String(a.artigo || "").localeCompare(String(b.artigo || ""), "pt-BR", { sensitivity: "base" })
        ));
}

function montarChaveArtigoBaseLegal(item, chaveLei, ordem) {
    if (item.artigo_id) return String(item.artigo_id);

    const artigoNumero = normalizarTextoChaveBaseLegal(item.artigo_numero);
    if (artigoNumero) {
        return `${chaveLei}|artigo|${artigoNumero}`;
    }

    const rotuloLegado = normalizarTextoChaveBaseLegal(limparRotuloArtigoLegadoBaseLegal(item.artigo));
    if (rotuloLegado) {
        return `${chaveLei}|artigo-legado|${rotuloLegado}`;
    }

    return `${chaveLei}|artigo-ordem|${ordem}`;
}

function montarChaveIncisoBaseLegal(item, chaveArtigo, ordem) {
    if (item.inciso_id) return String(item.inciso_id);

    const incisoNumero = normalizarTextoChaveBaseLegal(item.inciso_numero);
    if (incisoNumero) {
        return `${chaveArtigo}|inciso|${incisoNumero}`;
    }

    return `${chaveArtigo}|inciso-ordem|${ordem}`;
}

function montarChaveAlineaBaseLegal(item, chaveInciso, ordem) {
    if (item.alinea_id) return String(item.alinea_id);

    const alineaIdentificador = normalizarTextoChaveBaseLegal(item.alinea_identificador);
    if (alineaIdentificador) {
        return `${chaveInciso}|alinea|${alineaIdentificador}`;
    }

    return `${chaveInciso}|alinea-ordem|${ordem}`;
}

function ordenarColecaoBaseLegal(itens, campoTexto) {
    return Array.from(itens.values()).sort((a, b) => (
        Number(a.ordem || 0) - Number(b.ordem || 0)
        || String(a[campoTexto] || "").localeCompare(String(b[campoTexto] || ""), "pt-BR", { sensitivity: "base" })
    ));
}

function construirEstruturaBaseLegal(itens) {
    const leis = new Map();

    normalizarItensBaseLegal(itens).forEach((item) => {
        const ordem = Number(item.ordem || 0);
        const chaveLei = String(item.lei_nome || "__sem_lei__").trim() || "__sem_lei__";
        let lei = leis.get(chaveLei);
        if (!lei) {
            lei = {
                nome: String(item.lei_nome || "").trim(),
                ordem,
                artigos: new Map()
            };
            leis.set(chaveLei, lei);
        } else {
            lei.ordem = Math.min(Number(lei.ordem || ordem), ordem);
        }

        const chaveArtigo = montarChaveArtigoBaseLegal(item, chaveLei, ordem);
        let artigo = lei.artigos.get(chaveArtigo);
        if (!artigo) {
            artigo = {
                ordem,
                numero: item.artigo_numero,
                descricao: item.artigo_descricao,
                rotulo_legado: String(item.artigo || "").trim(),
                incisos: new Map()
            };
            lei.artigos.set(chaveArtigo, artigo);
        } else {
            artigo.ordem = Math.min(Number(artigo.ordem || ordem), ordem);
            if (item.artigo_numero && !artigo.numero) artigo.numero = item.artigo_numero;
            if (item.artigo_descricao && !artigo.descricao) artigo.descricao = item.artigo_descricao;
            if (item.artigo && !artigo.rotulo_legado) artigo.rotulo_legado = String(item.artigo || "").trim();
        }

        if (item.tipo === "artigo" && !item.inciso_numero && !item.alinea_identificador) {
            return;
        }

        const chaveInciso = montarChaveIncisoBaseLegal(item, chaveArtigo, ordem);
        let inciso = artigo.incisos.get(chaveInciso);
        if (!inciso) {
            inciso = {
                ordem,
                numero: item.inciso_numero,
                descricao: item.inciso_descricao,
                alineas: new Map()
            };
            artigo.incisos.set(chaveInciso, inciso);
        } else {
            inciso.ordem = Math.min(Number(inciso.ordem || ordem), ordem);
            if (item.inciso_numero && !inciso.numero) inciso.numero = item.inciso_numero;
            if (item.inciso_descricao && !inciso.descricao) inciso.descricao = item.inciso_descricao;
        }

        if (item.tipo !== "alinea" && !item.alinea_identificador) {
            return;
        }

        const chaveAlinea = montarChaveAlineaBaseLegal(item, chaveInciso, ordem);
        let alinea = inciso.alineas.get(chaveAlinea);
        if (!alinea) {
            alinea = {
                ordem,
                identificador: item.alinea_identificador,
                descricao: item.alinea_descricao
            };
            inciso.alineas.set(chaveAlinea, alinea);
        } else {
            alinea.ordem = Math.min(Number(alinea.ordem || ordem), ordem);
            if (item.alinea_identificador && !alinea.identificador) alinea.identificador = item.alinea_identificador;
            if (item.alinea_descricao && !alinea.descricao) alinea.descricao = item.alinea_descricao;
        }
    });

    const leisOrdenadas = Array.from(leis.values())
        .sort((a, b) => (
            Number(a.ordem || 0) - Number(b.ordem || 0)
            || String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR", { sensitivity: "base" })
        ))
        .map((lei) => ({
            ...lei,
            artigos: ordenarColecaoBaseLegal(lei.artigos, "numero").map((artigo) => ({
                ...artigo,
                incisos: ordenarColecaoBaseLegal(artigo.incisos, "numero").map((inciso) => ({
                    ...inciso,
                    alineas: ordenarColecaoBaseLegal(inciso.alineas, "identificador")
                }))
            }))
        }));

    const totalLeisNomeadas = leisOrdenadas.filter((lei) => String(lei.nome || "").trim()).length;
    return {
        leis: leisOrdenadas,
        mostrarLei: totalLeisNomeadas > 1
    };
}

function criarElementoTextoBaseLegal(tagName, className, texto) {
    const elemento = document.createElement(tagName);
    if (className) {
        elemento.className = className;
    }
    elemento.innerText = texto;
    return elemento;
}

function construirFragmentoBaseLegalAgrupada(itens, classes) {
    const estrutura = construirEstruturaBaseLegal(itens);
    if (!estrutura.leis.length) return null;

    const fragmento = document.createDocumentFragment();
    estrutura.leis.forEach((lei) => {
        if (estrutura.mostrarLei && lei.nome) {
            fragmento.appendChild(
                criarElementoTextoBaseLegal("div", classes.law, lei.nome)
            );
        }

        lei.artigos.forEach((artigo) => {
            const grupo = document.createElement("div");
            grupo.className = classes.group;
            grupo.appendChild(
                criarElementoTextoBaseLegal(
                    "strong",
                    `${classes.line} is-artigo`,
                    formatarLinhaArtigoBaseLegal(artigo.numero, artigo.descricao, artigo.rotulo_legado)
                )
            );

            artigo.incisos.forEach((inciso) => {
                const textoInciso = formatarLinhaIncisoBaseLegal(inciso.numero, inciso.descricao);
                if (textoInciso) {
                    grupo.appendChild(
                        criarElementoTextoBaseLegal("span", `${classes.line} is-inciso`, textoInciso)
                    );
                }

                inciso.alineas.forEach((alinea) => {
                    const textoAlinea = formatarLinhaAlineaBaseLegal(alinea.identificador, alinea.descricao);
                    if (textoAlinea) {
                        grupo.appendChild(
                            criarElementoTextoBaseLegal("span", `${classes.line} is-alinea`, textoAlinea)
                        );
                    }
                });
            });

            fragmento.appendChild(grupo);
        });
    });

    return fragmento;
}

function romanoParaInteiroBaseLegal(valor) {
    const texto = String(valor || "").trim().toUpperCase();
    if (!texto) return null;
    const mapa = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };
    let total = 0;
    let anterior = 0;

    for (let indice = texto.length - 1; indice >= 0; indice -= 1) {
        const simbolo = texto[indice];
        const atual = mapa[simbolo];
        if (!atual) return null;
        if (atual < anterior) {
            total -= atual;
        } else {
            total += atual;
            anterior = atual;
        }
    }
    return total;
}

function extrairReferenciaItemBaseLegal(item) {
    const artigoRotulo = String(item?.artigo || "").trim();
    let artigoNumero = String(item?.artigo_numero || "").trim().replace(/^art\.?\s*/i, "");
    let incisoNumero = String(item?.inciso_numero || "").trim().toUpperCase();

    if (!artigoNumero && artigoRotulo) {
        const matchArtigo = artigoRotulo.match(/Art\.?\s*([^\s,;:-]+(?:[-A-Za-z0-9.]+)?)/i);
        if (matchArtigo?.[1]) {
            artigoNumero = String(matchArtigo[1]).trim().replace(/^art\.?\s*/i, "");
        }
    }
    if (!incisoNumero && artigoRotulo) {
        const matchInciso = artigoRotulo.match(/(?:inciso\s+([IVXLCDM]+)|-\s*([IVXLCDM]+)\b)/i);
        if (matchInciso?.[1] || matchInciso?.[2]) {
            incisoNumero = String(matchInciso[1] || matchInciso[2] || "").trim().toUpperCase();
        }
    }

    return {
        artigoNumero,
        incisoNumero
    };
}

function inferirGravidadeItemBaseLegal(item) {
    const { artigoNumero, incisoNumero } = extrairReferenciaItemBaseLegal(item);
    if (!artigoNumero) return "";

    if (artigoNumero === "76") {
        return "leve";
    }

    const incisoValor = romanoParaInteiroBaseLegal(incisoNumero);
    if (artigoNumero === "81" || artigoNumero === "82") {
        if (incisoValor === 1) return "leve";
        if (incisoValor === 2) return "grave";
        if (incisoValor === 3) return "gravissima";
        return "";
    }

    if (artigoNumero !== "77" || !incisoValor) {
        return "";
    }
    if (incisoValor >= 1 && incisoValor <= 7) return "leve";
    if (incisoValor >= 8 && incisoValor <= 13) return "grave";
    if (incisoValor >= 14 && incisoValor <= 26) return "gravissima";
    return "";
}

function inferirGravidadeOcorrenciaBaseLegal(itens) {
    let gravidadeFinal = "";
    let ordemFinal = 0;
    normalizarItensBaseLegal(itens).forEach((item) => {
        const gravidadeItem = inferirGravidadeItemBaseLegal(item);
        const ordemItem = ORDEM_GRAVIDADE[gravidadeItem] || 0;
        if (ordemItem > ordemFinal) {
            gravidadeFinal = gravidadeItem;
            ordemFinal = ordemItem;
        }
    });
    return gravidadeFinal;
}

function obterAcoesAplicadasDisponiveis(gravidade, acaoAtual = "") {
    const acaoAtualLimpa = String(acaoAtual || "").trim();
    const acoes = Array.isArray(opcoesOcorrencias.acoes_aplicadas)
        ? opcoesOcorrencias.acoes_aplicadas
        : [];
    const detalhadas = acoes.filter((item) => !Boolean(item?.legado));
    const filtradas = gravidade
        ? detalhadas.filter((item) => String(item?.gravidade || "").trim() === gravidade)
        : detalhadas;

    const opcoes = filtradas.length > 0 ? filtradas : detalhadas;
    if (!acaoAtualLimpa) return opcoes;

    const atual = acoes.find((item) => String(item?.id || "").trim() === acaoAtualLimpa);
    if (!atual) return opcoes;
    if (opcoes.some((item) => String(item?.id || "").trim() === acaoAtualLimpa)) {
        return opcoes;
    }
    return [...opcoes, atual];
}

function atualizarAcaoAplicadaPorGravidade({
    manterValorAtual = true,
    gravidade = "",
    acaoAtual = null
} = {}) {
    const select = el("ocorrenciaAcaoAplicada");
    if (!select) return "";

    const valorAtual = acaoAtual === null
        ? String(select.value || "").trim()
        : String(acaoAtual || "").trim();
    const opcoes = obterAcoesAplicadasDisponiveis(gravidade, valorAtual);
    const placeholder = gravidade
        ? "Selecione a acao permitida"
        : "Selecione a acao aplicada";

    preencherSelect("ocorrenciaAcaoAplicada", opcoes, {
        placeholder
    });

    if (manterValorAtual && valorAtual && opcoes.some((item) => String(item.id) === valorAtual)) {
        select.value = valorAtual;
    }

    const hint = el("ocorrenciaGravidadeInfo");
    if (hint) {
        hint.innerText = gravidade
            ? `Gravidade automatica: ${GRAVIDADE_ROTULOS[gravidade] || gravidade}.`
            : "Gravidade automatica ainda nao identificada pela base legal selecionada.";
    }

    return gravidade;
}

function obterTurmaPreviewFormulario() {
    const turmaId = el("ocorrenciaTurmaId")?.value;
    const turma = obterTurmaOpcaoPorId(turmaId);
    if (turma?.nome) return turma.nome;

    const select = el("ocorrenciaTurmaId");
    const opcao = select?.selectedOptions?.[0];
    return obterTextoOuPadrao(opcao?.textContent, "Nao informada");
}

function obterAulaPreviewFormulario() {
    const select = el("ocorrenciaAula");
    const opcao = select?.selectedOptions?.[0];
    const textoOpcao = String(opcao?.textContent || "").trim();
    if (textoOpcao && !opcao?.disabled) {
        return textoOpcao;
    }

    const valor = String(select?.value || "").trim();
    return valor || "Nao informada";
}

function obterHorarioPreviewFormulario() {
    const horario = String(el("ocorrenciaHorario")?.value || "").trim();
    return horario ? `As ${horario} h` : "Nao informado";
}

function obterObservacaoFinalPreview(acaoAplicada) {
    const acao = String(acaoAplicada || "").trim();
    return OBSERVACOES_ACAO_PREVIEW[acao] || `OBS.: Documento emitido para registro e acompanhamento da acao aplicada: ${rotuloAcao(acao)}.`;
}

function obterItensRegimentoSelecionadosPreview() {
    const idsSelecionados = new Set(obterIdsRegimentoSelecionadosFormulario());
    return (opcoesOcorrencias.regimento_itens || []).filter((item) => idsSelecionados.has(Number(item?.id || 0)));
}

function atualizarCabecalhoPreviewOcorrencia(acaoAplicada, gravidade) {
    const titulo = el("previewTituloDocumento");
    if (titulo) {
        const rotulo = String(rotuloAcao(acaoAplicada) || "").trim();
        titulo.innerText = rotulo ? rotulo.toUpperCase() : "REGISTRO DE OCORRENCIAS DISCIPLINARES";
    }

    const previewGravidade = el("previewGravidade");
    if (previewGravidade) {
        previewGravidade.innerText = `Gravidade: ${GRAVIDADE_ROTULOS[gravidade] || "Nao identificada"}`;
    }
}

function definirTextoPreview(id, valor, padrao = "Nao informado") {
    const target = el(id);
    if (!target) return;
    target.innerText = obterTextoOuPadrao(valor, padrao);
}

function renderizarBaseLegalPreview(itens) {
    const container = el("previewBaseLegal");
    if (!container) return;

    container.innerHTML = "";
    if (!Array.isArray(itens) || itens.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-preview-empty";
        vazio.innerText = "Nenhuma base legal anexada ainda.";
        container.appendChild(vazio);
        return;
    }

    const fragmento = construirFragmentoBaseLegalAgrupada(itens, {
        group: "coordenacao-preview-legal-item",
        line: "coordenacao-preview-legal-line",
        law: "coordenacao-preview-legal-law"
    });

    if (!fragmento) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-preview-empty";
        vazio.innerText = "Nenhuma base legal anexada ainda.";
        container.appendChild(vazio);
        return;
    }

    container.appendChild(fragmento);
}

function atualizarPreviewOcorrencia() {
    if (!el("ocorrenciaPreviewPdf")) return;
    sincronizarDescricaoEditor();

    const ocorrenciaAtual = obterOcorrenciaEmEdicaoAtual();
    const estudante = el("ocorrenciaBuscaEstudante")?.value;
    const professor = el("ocorrenciaBuscaProfessor")?.value;
    const disciplina = el("ocorrenciaDisciplina")?.value;
    const descricao = el("ocorrenciaDescricao")?.value;
    const descricaoFormatada = el("ocorrenciaDescricaoFormatada")?.value;
    const dataOcorrencia = el("ocorrenciaData")?.value;
    const acaoAplicada = el("ocorrenciaAcaoAplicada")?.value;
    const status = el("ocorrenciaStatus")?.value;
    const itensRegimentoSelecionados = obterItensRegimentoSelecionadosPreview();
    const gravidade = inferirGravidadeOcorrenciaBaseLegal(itensRegimentoSelecionados);

    definirTextoPreview("previewNomeEstudante", estudante);
    definirTextoPreview("previewTurma", obterTurmaPreviewFormulario(), "Nao informada");
    definirTextoPreview("previewProfessor", professor);
    definirTextoPreview("previewDisciplina", disciplina, "Nao informada");
    definirTextoPreview("previewData", formatarDataBr(dataOcorrencia), "Nao informada");
    definirTextoPreview("previewAula", obterAulaPreviewFormulario(), "Nao informada");
    definirTextoPreview("previewHorario", obterHorarioPreviewFormulario(), "Nao informado");
    definirTextoPreview("previewAcao", rotuloAcao(acaoAplicada), "Nao informada");
    definirTextoPreview("previewStatus", rotuloStatus(status), "Nao informado");
    atualizarCabecalhoPreviewOcorrencia(acaoAplicada, gravidade);

    const descricaoPreview = el("previewDescricao");
    if (descricaoPreview) {
        renderizarDescricaoFormatada(
            descricaoPreview,
            descricaoFormatada,
            descricao,
            "A descricao digitada no formulario aparecera aqui automaticamente."
        );
    }

    renderizarBaseLegalPreview(itensRegimentoSelecionados);

    const observacaoPreview = el("previewObservacao");
    if (observacaoPreview) {
        observacaoPreview.innerText = obterObservacaoFinalPreview(acaoAplicada);
    }

    const emitidoEm = ocorrenciaAtual?.criado_em
        ? `Emitido em ${formatarDataHora(ocorrenciaAtual.criado_em)}`
        : `Emitido em ${new Date().toLocaleString("pt-BR")}`;
    definirTextoPreview("previewEmitidoEm", emitidoEm, "Emitido automaticamente no momento do registro.");
}

function atualizarSelectAulasPorTurma(turmaId, faixaSelecionada = null) {
    const select = el("ocorrenciaAula");
    const turma = obterTurmaOpcaoPorId(turmaId);

    select.innerHTML = "";
    if (!turma || !turma.turno_valido || Number(turma.aulas || 0) <= 0) {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = "Configure o turno da turma no painel admin";
        option.disabled = true;
        option.selected = true;
        select.appendChild(option);
        select.disabled = true;
        return;
    }

    const faixasTurma = faixasDisponiveisTurma(turma);
    const faixasManha = faixasTurma.filter((faixa) => faixa <= MAX_AULAS_EXIBICAO);
    const faixasTarde = faixasTurma.filter((faixa) => faixa > MAX_AULAS_EXIBICAO);

    const adicionarSeparadorTurno = (rotulo) => {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = `----- ${rotulo} -----`;
        option.disabled = true;
        select.appendChild(option);
    };

    const adicionarOpcaoFaixa = (faixa) => {
        const aulaTurno = aulaTurnoPorFaixa(turma.turno, faixa);
        const option = document.createElement("option");
        option.value = String(faixa);
        option.innerText = aulaTurno > 0
            ? `${aulaLabel(aulaTurno)}`
            : `Faixa ${faixa}`;
        select.appendChild(option);
    };

    if (faixasManha.length > 0) {
        adicionarSeparadorTurno("Matutino");
        faixasManha.forEach(adicionarOpcaoFaixa);
    }
    if (faixasTarde.length > 0) {
        adicionarSeparadorTurno("Vespertino");
        faixasTarde.forEach(adicionarOpcaoFaixa);
    }

    select.disabled = false;
    const faixaPreferida = Number(faixaSelecionada || 0);
    if (faixaPreferida > 0 && faixasTurma.includes(faixaPreferida)) {
        select.value = String(faixaPreferida);
    } else {
        select.value = faixasTurma.length > 0 ? String(faixasTurma[0]) : "";
    }
}

function limparFormularioOcorrencia({ manterAberto = false } = {}) {
    el("formOcorrencia").reset();
    definirDescricaoEditor();
    ocorrenciaEmEdicaoId = null;
    el("ocorrenciaEstudanteId").value = "";
    el("ocorrenciaProfessorRequerenteId").value = "";
    ocultarTodasSugestoes();

    const turmaSelect = el("ocorrenciaTurmaId");
    if (opcoesOcorrencias.turmas.length > 0) {
        turmaSelect.value = String(opcoesOcorrencias.turmas[0].id);
    }
    atualizarSelectAulasPorTurma(turmaSelect.value);

    const hoje = new Date();
    el("ocorrenciaData").value = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}-${String(hoje.getDate()).padStart(2, "0")}`;
    if (opcoesOcorrencias.status_padrao) {
        el("ocorrenciaStatus").value = opcoesOcorrencias.status_padrao;
    }
    renderSelecionadorRegimento([]);
    el("tituloFormOcorrencia").innerText = "Nova ocorrencia";
    el("btnCancelarEdicaoOcorrencia").style.display = "none";
    if (manterAberto) {
        mostrarPainelFormularioOcorrencia();
    } else {
        ocultarPainelFormularioOcorrencia();
    }
    atualizarPreviewOcorrencia();
}

function preencherFormularioOcorrencia(ocorrencia) {
    ocorrenciaEmEdicaoId = Number(ocorrencia.id);
    el("ocorrenciaBuscaEstudante").value = ocorrencia.nome_estudante || "";
    el("ocorrenciaEstudanteId").value = ocorrencia.estudante_id || "";
    el("ocorrenciaBuscaRegimento").value = "";

    const turmaId = String(ocorrencia.turma_id || "");
    el("ocorrenciaTurmaId").value = turmaId;

    const turmaAtual = obterTurmaOpcaoPorId(turmaId);
    const faixaAula = resolverFaixaOcorrenciaParaTurma(turmaAtual, ocorrencia.aula);
    atualizarSelectAulasPorTurma(turmaId, faixaAula);

    const professorPorId = obterProfessorOpcaoPorId(ocorrencia.professor_requerente_id);
    if (professorPorId) {
        el("ocorrenciaBuscaProfessor").value = professorPorId.label || professorPorId.nome || "";
        el("ocorrenciaProfessorRequerenteId").value = String(professorPorId.id);
    } else {
        const professorPorNome = (opcoesOcorrencias.professores || []).find(
            (professor) => String(professor.nome || "").trim().toLowerCase() === String(ocorrencia.professor_requerente || "").trim().toLowerCase()
        );
        el("ocorrenciaBuscaProfessor").value = professorPorNome
            ? (professorPorNome.label || professorPorNome.nome || "")
            : (ocorrencia.professor_requerente || "");
        el("ocorrenciaProfessorRequerenteId").value = professorPorNome ? String(professorPorNome.id) : "";
    }

    el("ocorrenciaDisciplina").value = ocorrencia.disciplina || "";
    el("ocorrenciaData").value = ocorrencia.data_ocorrencia || "";
    el("ocorrenciaHorario").value = ocorrencia.horario_ocorrencia || "";
    definirDescricaoEditor({
        texto: ocorrencia.descricao || "",
        html: ocorrencia.descricao_formatada || ""
    });
    renderSelecionadorRegimento(obterIdsRegimentoSelecionadosOcorrencia(ocorrencia));
    atualizarAcaoAplicadaPorGravidade({
        gravidade: inferirGravidadeOcorrenciaBaseLegal(obterItensRegimentoSelecionadosPreview()),
        acaoAtual: ocorrencia.acao_aplicada || ""
    });
    el("ocorrenciaStatus").value = ocorrencia.status || opcoesOcorrencias.status_padrao || "registrado";
    el("tituloFormOcorrencia").innerText = "Editar ocorrencia";
    el("btnCancelarEdicaoOcorrencia").style.display = "inline-block";
    ativarAbaCoordenacao("ocorrencias");
    mostrarPainelFormularioOcorrencia({ scroll: true });
    atualizarPreviewOcorrencia();
}

function selecionarOcorrencia(ocorrencia) {
    ocorrenciaSelecionadaId = ocorrencia ? Number(ocorrencia.id || 0) || null : null;
    renderDetalhesOcorrencia(ocorrencia || null);
    renderTabelaOcorrencias();
}

function obterNomeArquivoContentDisposition(contentDisposition, ocorrencia) {
    const header = String(contentDisposition || "");
    const match = header.match(/filename="?([^";]+)"?/i);
    if (match && match[1]) {
        return match[1];
    }

    const nomeBase = String(ocorrencia?.nome_estudante || "ocorrencia")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "") || "ocorrencia";
    return `registro_ocorrencia_${nomeBase}.pdf`;
}

async function abrirPdfOcorrencia(ocorrencia) {
    if (!ocorrencia?.id) {
        setMensagemOcorrencias("Selecione uma ocorrencia valida para gerar o PDF.", true);
        return;
    }

    let blobUrl = "";
    setMensagemOcorrencias("Gerando PDF da ocorrencia...");

    try {
        const resposta = await fetchResposta(`/ocorrencias/${ocorrencia.id}/pdf`, { headers });
        const blob = await resposta.blob();
        const nomeArquivo = obterNomeArquivoContentDisposition(
            resposta.headers.get("content-disposition"),
            ocorrencia
        );

        blobUrl = URL.createObjectURL(blob);
        const novaGuia = window.open(blobUrl, "_blank", "noopener");

        if (!novaGuia) {
            const link = document.createElement("a");
            link.href = blobUrl;
            link.download = nomeArquivo;
            document.body.appendChild(link);
            link.click();
            link.remove();
            setMensagemOcorrencias("PDF gerado e baixado para impressao.");
        } else {
            novaGuia.focus();
            setMensagemOcorrencias("PDF gerado e aberto em nova guia.");
        }

        window.setTimeout(() => {
            URL.revokeObjectURL(blobUrl);
        }, 60000);
    } catch (err) {
        if (blobUrl) {
            URL.revokeObjectURL(blobUrl);
        }
        setMensagemOcorrencias(
            err?.message || "Nao foi possivel gerar o PDF da ocorrencia.",
            true
        );
    }
}

function criarBlocoDetalhesRegimento(ocorrencia) {
    const wrapper = document.createElement("div");
    wrapper.className = "coordenacao-detail-block";

    const titulo = document.createElement("strong");
    titulo.className = "coordenacao-detail-block-title";
    titulo.innerText = "Base legal vinculada";
    wrapper.appendChild(titulo);

    const itens = Array.isArray(ocorrencia?.regimento_itens) ? ocorrencia.regimento_itens : [];
    if (itens.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-detail-hint";
        vazio.innerText = "Nenhum item de base legal vinculado a esta ocorrencia.";
        wrapper.appendChild(vazio);
        return wrapper;
    }

    const lista = document.createElement("div");
    lista.className = "coordenacao-detail-list";
    const fragmento = construirFragmentoBaseLegalAgrupada(itens, {
        group: "coordenacao-detail-list-item",
        line: "coordenacao-detail-line",
        law: "coordenacao-detail-list-law"
    });
    if (fragmento) {
        lista.appendChild(fragmento);
    }

    wrapper.appendChild(lista);
    return wrapper;
}

function renderDetalhesOcorrencia(ocorrencia) {
    const container = el("detalhesOcorrencia");
    if (!container) return;
    if (!ocorrencia) {
        container.innerText = "Selecione uma ocorrencia para visualizar os detalhes.";
        return;
    }

    container.innerHTML = "";
    const actions = document.createElement("div");
    actions.className = "coordenacao-detail-actions";

    const btnPdf = document.createElement("button");
    btnPdf.type = "button";
    btnPdf.className = "btn-destaque";
    btnPdf.innerText = "Gerar PDF para impressao";
    btnPdf.addEventListener("click", () => {
        abrirPdfOcorrencia(ocorrencia);
    });
    actions.appendChild(btnPdf);
    container.appendChild(actions);

    const hint = document.createElement("p");
    hint.className = "coordenacao-detail-hint";
    hint.innerText = "Use este documento para impressao e anexo fisico no livro de registro.";
    container.appendChild(hint);

    const campos = [
        ["Estudante", ocorrencia.nome_estudante],
        ["Turma", ocorrencia.turma_nome || `ID ${ocorrencia.turma_id}`],
        ["Professor requerente", ocorrencia.professor_requerente],
        ["Disciplina", ocorrencia.disciplina],
        ["Data", formatarDataBr(ocorrencia.data_ocorrencia)],
        ["Aula", formatarAulaOcorrencia(ocorrencia)],
        ["Horario", ocorrencia.horario_ocorrencia],
        ["Acao aplicada", rotuloAcao(ocorrencia.acao_aplicada)],
        ["Status", rotuloStatus(ocorrencia.status)],
        ["Descricao", ocorrencia.descricao],
        ["Criado em", formatarDataHora(ocorrencia.criado_em)],
        ["Atualizado em", formatarDataHora(ocorrencia.atualizado_em)]
    ];

    campos.forEach(([rotulo, valor]) => {
        const linha = document.createElement(rotulo === "Descricao" ? "div" : "p");
        linha.className = "coordenacao-detail-line";
        const strong = document.createElement("strong");
        strong.innerText = `${rotulo}: `;
        const span = document.createElement("span");
        if (rotulo === "Descricao") {
            renderizarDescricaoFormatada(
                span,
                ocorrencia.descricao_formatada || "",
                ocorrencia.descricao || "",
                "Nao informado"
            );
        } else {
            span.innerText = valor || "Nao informado";
        }
        linha.appendChild(strong);
        linha.appendChild(span);
        container.appendChild(linha);
    });

    container.appendChild(criarBlocoDetalhesRegimento(ocorrencia));
}


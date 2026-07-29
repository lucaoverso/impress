async function salvarRegistroDocente(event) {
    event.preventDefault();
    limparMensagem("msgPreconselhoRegistro");

    const periodo = periodoDocenteAtual();
    const combo = comboDocenteAtual();
    const estudanteId = Number(estadoDocente.estudanteId || 0);
    const motivoIds = obterMotivosSelecionadosDocente();
    const observacao = String(el("preconselhoObservacaoProfessor").value || "").trim();
    const nivelAtencao = String(el("preconselhoNivelAtencao").value || "").trim() || null;
    const estudanteEmRav = periodoTemRav(periodo) && Boolean(el("preconselhoEstudanteEmRav").checked);
    const ravHabilidadeIds = estudanteEmRav ? obterHabilidadesRavSelecionadasDocente() : [];
    const ravAcoes = estudanteEmRav ? String(el("preconselhoRavAcoes").value || "").trim() : "";

    if (!periodo || !combo) {
        definirMensagem("msgPreconselhoRegistro", "Selecione um período e uma turma/disciplina antes de salvar.", true);
        return;
    }
    if (!estudanteId) {
        definirMensagem("msgPreconselhoRegistro", "Selecione um estudante para continuar.", true);
        return;
    }
    if (!periodo.editavel) {
        definirMensagem("msgPreconselhoRegistro", "O período selecionado está fechado para edição.", true);
        return;
    }

    try {
        if (motivoIds.length === 0) {
            definirMensagem("msgPreconselhoRegistro", "Selecione ao menos um motivo para salvar o registro.", true);
            return;
        }
        definirEstadoSalvamentoModal(true);

        const resposta = await fetchComAuth("/preconselho/registros", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                periodo_id: Number(periodo.id),
                turma_id: Number(combo.turma_id),
                disciplina_id: Number(combo.disciplina_id),
                estudante_id: estudanteId,
                sinalizar: true,
                motivo_ids: motivoIds,
                observacao_professor: observacao,
                nivel_atencao: nivelAtencao,
                pos_preconselho_recuperado: null,
                pos_preconselho_motivo_ids: [],
                pos_preconselho_observacao: "",
                estudante_em_rav: estudanteEmRav,
                rav_habilidade_ids: ravHabilidadeIds,
                rav_acoes: ravAcoes
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar o registro."));
        }

        const salvo = await resposta.json();
        const painelAtualizado = await carregarPainelDocente(Number(salvo.estudante_id));
        if (!painelAtualizado) {
            definirMensagem("msgPreconselhoRegistro", "Registro salvo, mas o painel não foi recarregado corretamente.", true);
            return;
        }
        definirMensagem("msgPreconselhoDocente", `Registro de ${String(salvo.estudante_nome || "estudante")} salvo com sucesso.`);
        modalDocenteAlterado = false;
        fecharModalRegistroDocente({ restaurarFoco: false, forcar: true });
    } catch (erro) {
        definirMensagem("msgPreconselhoRegistro", erro.message || "Erro ao salvar o registro.", true);
    } finally {
        definirEstadoSalvamentoModal(false);
    }
}

async function salvarReavaliacaoDocente() {
    limparMensagem("msgPreconselhoRegistro");
    const registro = registroDocenteAtual();
    const resultado = document.querySelector('[name="preconselhoResultadoReavaliacao"]:checked')?.value || "";
    const motivoIds = Array.from(document.querySelectorAll(".preconselho-review-reason:checked")).map((item) => item.value);
    if (!registro || !periodoEmReavaliacao()) {
        definirMensagem("msgPreconselhoRegistro", "Este registro não está disponível para reavaliação.", true);
        return;
    }
    if (!resultado || motivoIds.length === 0) {
        definirMensagem("msgPreconselhoRegistro", "Selecione o resultado e ao menos um motivo.", true);
        return;
    }
    try {
        definirEstadoSalvamentoModal(true);
        const resposta = await fetchComAuth(`/preconselho/registros/${Number(registro.id)}/reavaliacao`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                recuperado: resultado === "recuperado",
                motivo_ids: motivoIds,
                observacao: String(el("preconselhoObservacaoReavaliacao").value || "").trim()
            })
        });
        if (!resposta.ok) throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar a reavaliação."));
        const registroAtualizado = await resposta.json();
        aplicarReavaliacaoNoEstado(registroAtualizado);
        definirMensagem("msgPreconselhoDocente", "Reavaliação salva com sucesso.");
        modalDocenteAlterado = false;
        fecharModalRegistroDocente({ restaurarFoco: false, forcar: true });
    } catch (erro) {
        definirMensagem("msgPreconselhoRegistro", erro.message || "Erro ao salvar a reavaliação.", true);
    } finally {
        definirEstadoSalvamentoModal(false);
    }
}

async function excluirRegistroDocente(registroId) {
    const resposta = await fetchComAuth(`/preconselho/registros/${Number(registroId)}`, {
        method: "DELETE",
        headers
    });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível excluir o registro."));
    }
}

async function copiarTexto(idCampo, idMensagem, sucesso, opcoes = {}) {
    const campo = el(idCampo);
    const texto = String(campo?.value || "").trim();
    if (!texto) {
        definirMensagem(idMensagem, "Não há texto disponível para copiar.", true);
        return;
    }

    try {
        const html = typeof opcoes.html === "function" ? String(opcoes.html(texto) || "") : "";
        if (html && navigator.clipboard?.write && window.ClipboardItem) {
            await navigator.clipboard.write([
                new ClipboardItem({
                    "text/plain": new Blob([texto], { type: "text/plain" }),
                    "text/html": new Blob([html], { type: "text/html" }),
                }),
            ]);
        } else if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(texto);
        } else {
            campo.select();
            document.execCommand("copy");
        }
        definirMensagem(idMensagem, sucesso);
    } catch (_erro) {
        definirMensagem(idMensagem, "Não foi possível copiar o texto.", true);
    }
}


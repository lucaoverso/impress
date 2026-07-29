async function salvarPeriodo(event) {
    event.preventDefault();
    limparMensagem("msgPreconselhoPeriodo");

    const periodoId = Number(el("preconselhoPeriodoEdicaoId").value || 0);
    const payloadBase = {
        nome: String(el("preconselhoPeriodoNome").value || "").trim(),
        ano_letivo: Number(el("preconselhoPeriodoAnoLetivo").value || 0),
        etapa: Number(el("preconselhoPeriodoEtapa").value || 0),
        data_inicio: String(el("preconselhoPeriodoDataInicio").value || ""),
        data_fim: String(el("preconselhoPeriodoDataFim").value || ""),
        tem_rav: Boolean(el("preconselhoPeriodoTemRav").checked)
    };
    const statusDesejado = String(el("preconselhoPeriodoStatusForm").value || "ABERTO");

    try {
        let resposta;
        if (periodoId > 0) {
            resposta = await fetchComAuth(`/preconselho/periodos/${periodoId}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payloadBase)
            });
        } else {
            resposta = await fetchComAuth("/preconselho/periodos", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify({
                    ...payloadBase,
                    status: statusDesejado
                })
            });
        }

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar o período."));
        }

        const periodoSalvo = await resposta.json();
        if (periodoId > 0 && String(periodoSalvo.status || "") !== statusDesejado) {
            const respostaStatus = await fetchComAuth(`/preconselho/periodos/${periodoSalvo.id}/status`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify({ status: statusDesejado })
            });
            if (!respostaStatus.ok) {
                throw new Error(await obterMensagemErroResposta(respostaStatus, "O período foi salvo, mas o status não foi atualizado."));
            }
        }

        await recarregarPeriodos();
        renderizarSelectsConsolidacao();
        renderizarSelectDisciplinaHabilidadeRav();
        if (contextoAtual?.pode_consolidar) {
            await carregarConsolidacao();
        }
        if (contextoAtual?.pode_relatorio) {
            await carregarRelatorio();
            await carregarRav();
        }
        limparFormularioPeriodo();
        definirMensagem("msgPreconselhoPeriodo", periodoId > 0 ? "Período atualizado com sucesso." : "Período criado com sucesso.");
    } catch (erro) {
        definirMensagem("msgPreconselhoPeriodo", erro.message || "Erro ao salvar o período.", true);
    }
}

async function alternarStatusPeriodo(periodoId, statusAtual) {
    limparMensagem("msgPreconselhoPeriodo");
    const statusNormalizado = String(statusAtual || "").toUpperCase();
    const proximoStatus = statusNormalizado === "ABERTO"
        ? "EM_REAVALIACAO"
        : (statusNormalizado === "EM_REAVALIACAO" ? "ENCERRADO" : "EM_REAVALIACAO");
    try {
        const resposta = await fetchComAuth(`/preconselho/periodos/${Number(periodoId)}/status`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                status: proximoStatus
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível atualizar o status do período."));
        }

        await recarregarPeriodos();
        renderizarSelectsConsolidacao();
        renderizarSelectDisciplinaHabilidadeRav();
        if (contextoAtual?.pode_consolidar) {
            await carregarConsolidacao();
        }
        if (contextoAtual?.pode_relatorio) {
            await carregarRelatorio();
            await carregarRav();
        }
        definirMensagem("msgPreconselhoPeriodo", "Status do período atualizado.");
    } catch (erro) {
        definirMensagem("msgPreconselhoPeriodo", erro.message || "Erro ao atualizar o status do período.", true);
    }
}

async function salvarMotivo(event) {
    event.preventDefault();
    limparMensagem("msgPreconselhoMotivo");

    const motivoId = Number(el("preconselhoMotivoEdicaoId").value || 0);
    const payload = {
        categoria: String(el("preconselhoMotivoCategoria").value || ""),
        descricao: String(el("preconselhoMotivoDescricao").value || "").trim(),
        ordem: Number(el("preconselhoMotivoOrdem").value || 0)
    };

    try {
        let resposta;
        if (motivoId > 0) {
            resposta = await fetchComAuth(`/preconselho/motivos/${motivoId}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
        } else {
            resposta = await fetchComAuth("/preconselho/motivos", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify({
                    ...payload,
                    codigo: String(el("preconselhoMotivoCodigo").value || "").trim()
                })
            });
        }

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar o motivo."));
        }

        await recarregarMotivos();
        limparFormularioMotivo();
        definirMensagem("msgPreconselhoMotivo", motivoId > 0 ? "Motivo atualizado com sucesso." : "Motivo criado com sucesso.");
    } catch (erro) {
        definirMensagem("msgPreconselhoMotivo", erro.message || "Erro ao salvar o motivo.", true);
    }
}

async function alternarStatusMotivo(motivoId, ativoAtual) {
    limparMensagem("msgPreconselhoMotivo");
    try {
        const resposta = await fetchComAuth(`/preconselho/motivos/${Number(motivoId)}/status`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                ativo: Number(ativoAtual) !== 1
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível atualizar o status do motivo."));
        }

        await recarregarMotivos();
        definirMensagem("msgPreconselhoMotivo", "Status do motivo atualizado.");
    } catch (erro) {
        definirMensagem("msgPreconselhoMotivo", erro.message || "Erro ao atualizar o status do motivo.", true);
    }
}

async function salvarHabilidadeRav(event) {
    event.preventDefault();
    limparMensagem("msgPreconselhoRavHabilidade");

    const habilidadeId = Number(el("preconselhoRavHabilidadeEdicaoId").value || 0);
    const payload = {
        periodo_id: Number(el("preconselhoRavHabilidadePeriodo").value || 0),
        disciplina_id: Number(el("preconselhoRavHabilidadeDisciplina").value || 0),
        codigo: String(el("preconselhoRavHabilidadeCodigo").value || "").trim(),
        descricao: String(el("preconselhoRavHabilidadeDescricao").value || "").trim(),
        turma_ids: Array.from(el("preconselhoRavHabilidadeTurmas").selectedOptions || [])
            .map((option) => Number(option.value || 0))
            .filter((valor) => Number.isInteger(valor) && valor > 0),
        ordem: Number(el("preconselhoRavHabilidadeOrdem").value || 0)
    };

    try {
        const resposta = await fetchComAuth(
            habilidadeId > 0 ? `/preconselho/habilidades-rav/${habilidadeId}` : "/preconselho/habilidades-rav",
            {
                method: habilidadeId > 0 ? "PUT" : "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            }
        );

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel salvar a habilidade de RAV."));
        }

        await recarregarHabilidadesRav();
        limparFormularioHabilidadeRav();
        definirMensagem("msgPreconselhoRavHabilidade", habilidadeId > 0 ? "Habilidade atualizada com sucesso." : "Habilidade criada com sucesso.");
    } catch (erro) {
        definirMensagem("msgPreconselhoRavHabilidade", erro.message || "Erro ao salvar a habilidade de RAV.", true);
    }
}

async function importarHabilidadesRavJson(event) {
    event.preventDefault();
    limparMensagem("msgPreconselhoRavImport");

    let payload;
    try {
        const texto = String(el("preconselhoRavImportJson").value || "").trim();
        const dados = JSON.parse(texto);
        const periodoPadrao = Number(el("preconselhoRavImportPeriodo").value || 0);
        payload = Array.isArray(dados)
            ? { periodo_id: periodoPadrao || null, habilidades: dados }
            : {
                periodo_id: periodoPadrao || dados.periodo_id || null,
                periodo: String(dados.periodo || ""),
                habilidades: dados.habilidades || []
            };
    } catch (erro) {
        definirMensagem("msgPreconselhoRavImport", "JSON invalido. Confira a estrutura antes de importar.", true);
        return;
    }

    try {
        const resposta = await fetchComAuth("/preconselho/habilidades-rav/importar-json", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify(payload)
        });
        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel importar as habilidades."));
        }
        const resultado = await resposta.json();
        await recarregarHabilidadesRav();
        definirMensagem(
            "msgPreconselhoRavImport",
            `Importacao concluida: ${Number(resultado.criadas || 0)} criadas, ${Number(resultado.atualizadas || 0)} atualizadas, ${Number(resultado.ignoradas || 0)} ignoradas.`
        );
        if (Array.isArray(resultado.erros) && resultado.erros.length > 0) {
            definirMensagem("msgPreconselhoRavImport", resultado.erros.slice(0, 4).join(" | "), true);
        }
    } catch (erro) {
        definirMensagem("msgPreconselhoRavImport", erro.message || "Erro ao importar habilidades.", true);
    }
}

async function alternarStatusHabilidadeRav(habilidadeId, ativoAtual) {
    limparMensagem("msgPreconselhoRavHabilidade");
    try {
        const resposta = await fetchComAuth(`/preconselho/habilidades-rav/${Number(habilidadeId)}/status`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                ativo: Number(ativoAtual) !== 1
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel atualizar o status da habilidade."));
        }

        await recarregarHabilidadesRav();
        definirMensagem("msgPreconselhoRavHabilidade", "Status da habilidade atualizado.");
    } catch (erro) {
        definirMensagem("msgPreconselhoRavHabilidade", erro.message || "Erro ao atualizar o status da habilidade.", true);
    }
}


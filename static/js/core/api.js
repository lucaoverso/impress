(function (window) {
    function encerrarSessaoFallback() {
        if (window.AppAuth && typeof window.AppAuth.encerrarSessao === "function") {
            window.AppAuth.encerrarSessao();
            return;
        }
        window.location.href = "/login-page";
    }

    function normalizarErro(res, body) {
        if (body && body.detail) return body.detail;
        return `Erro ${res.status}`;
    }

    function pareceHtml(texto) {
        const conteudo = String(texto || "").trim().toLowerCase();
        return conteudo.startsWith("<!doctype html") || conteudo.startsWith("<html");
    }

    function mensagemAmigavelHttp(res) {
        if (res.status === 502 || res.status === 503 || res.status === 504) {
            return "O servidor demorou para responder ou ficou indisponível. Tente novamente em alguns minutos.";
        }
        if (res.status >= 500) {
            return "O servidor encontrou um erro temporário. Tente novamente em alguns minutos.";
        }
        return `Erro ${res.status}`;
    }

    async function parseJsonSeguro(res) {
        try {
            return await res.json();
        } catch (_err) {
            return null;
        }
    }

    async function fetchJson(url, options = {}) {
        const res = await fetch(url, options);
        const body = await parseJsonSeguro(res);

        if (res.status === 401) {
            encerrarSessaoFallback();
            const erro = new Error("Sessão expirada.");
            erro.status = res.status;
            throw erro;
        }

        if (!res.ok) {
            const erro = new Error(normalizarErro(res, body));
            erro.status = res.status;
            erro.body = body;
            throw erro;
        }

        return body;
    }

    async function fetchComAuth(url, options = {}) {
        const res = await fetch(url, options);
        if (res.status === 401) {
            encerrarSessaoFallback();
            const erro = new Error("Sessão expirada.");
            erro.status = res.status;
            throw erro;
        }
        return res;
    }

    async function fetchResposta(url, options = {}) {
        const res = await fetch(url, options);

        if (res.status === 401) {
            encerrarSessaoFallback();
            const erro = new Error("Sessão expirada.");
            erro.status = res.status;
            throw erro;
        }

        if (!res.ok) {
            let detalhe = mensagemAmigavelHttp(res);
            const tipoConteudo = String(res.headers.get("content-type") || "").toLowerCase();
            if (tipoConteudo.includes("application/json")) {
                try {
                    const body = await res.json();
                    detalhe = normalizarErro(res, body);
                } catch (_err) {
                    detalhe = mensagemAmigavelHttp(res);
                }
            } else {
                try {
                    const texto = (await res.text()).trim();
                    if (texto && !pareceHtml(texto)) {
                        detalhe = texto;
                    }
                } catch (_err) {
                    detalhe = mensagemAmigavelHttp(res);
                }
            }

            const erro = new Error(detalhe);
            erro.status = res.status;
            throw erro;
        }

        return res;
    }

    async function obterMensagemErroResposta(resposta, fallback) {
        try {
            const dados = await resposta.json();
            if (typeof dados?.detail === "string" && dados.detail.trim()) {
                return dados.detail.trim();
            }
            if (typeof dados?.mensagem === "string" && dados.mensagem.trim()) {
                return dados.mensagem.trim();
            }
        } catch (_erro) {
            // Resposta sem JSON util.
        }
        return fallback;
    }

    function baixarArquivoTexto(nomeArquivo, conteudo, tipo = "text/plain;charset=utf-8") {
        const blob = new Blob(["\uFEFF", conteudo], { type: tipo });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = nomeArquivo;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    }

    window.AppApi = Object.assign(window.AppApi || {}, {
        normalizarErro,
        fetchJson,
        fetchComAuth,
        fetchResposta,
        obterMensagemErroResposta,
        baixarArquivoTexto,
    });
})(window);

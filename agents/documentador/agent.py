import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# Configurações gerais
# ============================================================

AGENT_DIR = Path(__file__).resolve().parent

# Estrutura esperada:
#
# sistema-impress/
# └── agents/
#     └── documentador/
#         └── agent.py
#
# Portanto, a raiz do projeto fica dois níveis acima:
# agent.py -> documentador -> agents -> raiz do projeto
PROJECT_ROOT = AGENT_DIR.parents[1]

SKILLS_DIR = AGENT_DIR / "skills"
CONTRACTS_DIR = AGENT_DIR / "contracts"

DOCS_OUTPUT_DIR = PROJECT_ROOT / "docs" / "geradas"

ENV_PATH = AGENT_DIR / ".env"

EXTENSOES_PERMITIDAS = {
    ".py",
    ".html",
    ".js",
    ".css",
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
}

PASTAS_IGNORADAS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
    "docs",
    "logs",
    "uploads",
    "spool",
    "outputs",
    "geradas",
}

ARQUIVOS_IGNORADOS = {
    ".env",
    ".env.local",
    ".env.production",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
}

MAX_CHARS_POR_ARQUIVO = 30_000
MAX_CHARS_TOTAL = 120_000


# ============================================================
# Inicialização da IA
# ============================================================

def criar_cliente_ia() -> tuple[OpenAI, str, str]:
    """
    Cria o cliente de IA com base no provedor escolhido no .env.

    AI_PROVIDER=openai
    ou
    AI_PROVIDER=openrouter
    """

    load_dotenv(ENV_PATH)

    provider = os.getenv("AI_PROVIDER", "openai").strip().lower()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

        if not api_key:
            print("\nERRO: OPENAI_API_KEY não encontrada.")
            print(f"Crie ou ajuste o arquivo .env em: {ENV_PATH}")
            sys.exit(1)

        client = OpenAI(api_key=api_key)

        return client, model, "OpenAI"

    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        site_url = os.getenv("OPENROUTER_SITE_URL", "http://localhost")
        app_name = os.getenv("OPENROUTER_APP_NAME", "Documentador de Sistema")

        if not api_key:
            print("\nERRO: OPENROUTER_API_KEY não encontrada.")
            print(f"Crie ou ajuste o arquivo .env em: {ENV_PATH}")
            sys.exit(1)

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": site_url,
                "X-OpenRouter-Title": app_name,
            },
        )

        return client, model, "OpenRouter"

    print(f"\nERRO: AI_PROVIDER inválido: {provider}")
    print("Use AI_PROVIDER=openai ou AI_PROVIDER=openrouter")
    sys.exit(1)


# ============================================================
# Leitura de arquivos de skill e contrato
# ============================================================

def ler_texto(caminho: Path) -> str:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    return caminho.read_text(encoding="utf-8", errors="ignore")


def carregar_skill(nome: str = "documentador_sistema.md") -> str:
    return ler_texto(SKILLS_DIR / nome)


def carregar_contract(nome: str = "documentacao_markdown.md") -> str:
    return ler_texto(CONTRACTS_DIR / nome)


# ============================================================
# Descoberta de módulos
# ============================================================

def deve_ignorar_pasta(path: Path) -> bool:
    return path.name in PASTAS_IGNORADAS


def deve_ignorar_arquivo(path: Path) -> bool:
    if path.name in ARQUIVOS_IGNORADOS:
        return True

    if path.suffix not in EXTENSOES_PERMITIDAS:
        return True

    return False


def caminho_tem_pasta_ignorada(path: Path) -> bool:
    return any(parte in PASTAS_IGNORADAS for parte in path.parts)


def contar_arquivos_relevantes(pasta: Path) -> int:
    total = 0

    for arquivo in pasta.rglob("*"):
        if caminho_tem_pasta_ignorada(arquivo):
            continue

        if arquivo.is_file() and not deve_ignorar_arquivo(arquivo):
            total += 1

    return total


def encontrar_modulos() -> list[Path]:
    """
    Procura pastas candidatas a módulo.

    Estratégia:
    1. Prioriza app/modules.
    2. Depois tenta app, src e backend.
    3. Se não encontrar, lista pastas relevantes da raiz.
    """

    candidatos_base = [
        PROJECT_ROOT / "app" / "modules",
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "src",
        PROJECT_ROOT / "backend",
    ]

    modulos: list[Path] = []

    for base in candidatos_base:
        if base.exists() and base.is_dir():
            for item in sorted(base.iterdir()):
                if item.is_dir() and not deve_ignorar_pasta(item):
                    if contar_arquivos_relevantes(item) > 0:
                        modulos.append(item)

            if modulos:
                return modulos

    # Fallback: pastas diretas da raiz
    for item in sorted(PROJECT_ROOT.iterdir()):
        if item.is_dir() and not deve_ignorar_pasta(item):
            if contar_arquivos_relevantes(item) > 0:
                modulos.append(item)

    return modulos


def exibir_modulos(modulos: list[Path]) -> None:
    print("\n======================================")
    print(" MÓDULOS ENCONTRADOS")
    print("======================================\n")

    for indice, modulo in enumerate(modulos, start=1):
        rel = modulo.relative_to(PROJECT_ROOT)
        qtd = contar_arquivos_relevantes(modulo)
        print(f"{indice:02d} - {rel} ({qtd} arquivos relevantes)")

    print("\n00 - Digitar caminho manualmente")
    print("99 - Sair")


def escolher_modulo(modulos: list[Path]) -> Path | None:
    while True:
        escolha = input("\nEscolha o módulo que deseja documentar: ").strip()

        if escolha == "99":
            return None

        if escolha == "00":
            caminho = input(
                "\nDigite o caminho da pasta ou arquivo a partir da raiz do projeto:\n> "
            ).strip()

            alvo = PROJECT_ROOT / caminho

            if alvo.exists():
                return alvo

            print(f"\nCaminho não encontrado: {alvo}")
            continue

        if not escolha.isdigit():
            print("\nDigite um número válido.")
            continue

        indice = int(escolha)

        if 1 <= indice <= len(modulos):
            return modulos[indice - 1]

        print("\nOpção inválida.")


# ============================================================
# Leitura do módulo
# ============================================================

def gerar_arvore_resumida(pasta: Path) -> str:
    linhas = []

    for arquivo in sorted(pasta.rglob("*")):
        if arquivo.is_dir():
            continue

        if caminho_tem_pasta_ignorada(arquivo):
            continue

        if deve_ignorar_arquivo(arquivo):
            continue

        rel = arquivo.relative_to(PROJECT_ROOT)
        linhas.append(f"- {rel}")

    if not linhas:
        return "> Nenhum arquivo relevante identificado."

    return "\n".join(linhas)


def ler_arquivo_para_prompt(arquivo: Path) -> str:
    rel = arquivo.relative_to(PROJECT_ROOT)

    try:
        conteudo = arquivo.read_text(encoding="utf-8", errors="ignore")
    except Exception as erro:
        return f"""

================================================================================
ARQUIVO: {rel}
================================================================================

ERRO AO LER ARQUIVO: {erro}
"""

    if len(conteudo) > MAX_CHARS_POR_ARQUIVO:
        conteudo = conteudo[:MAX_CHARS_POR_ARQUIVO]
        conteudo += "\n\n[CONTEÚDO CORTADO: arquivo muito grande]\n"

    return f"""

================================================================================
ARQUIVO: {rel}
================================================================================

{conteudo}
"""


def ler_modulo(alvo: Path) -> tuple[str, str]:
    """
    Retorna:
    - nome do módulo
    - conteúdo consolidado para mandar ao modelo
    """

    if alvo.is_file():
        nome_modulo = alvo.stem
        conteudo = ler_arquivo_para_prompt(alvo)
        return nome_modulo, conteudo

    nome_modulo = alvo.name
    partes = []

    arvore = gerar_arvore_resumida(alvo)

    bloco_arvore = f"""
================================================================================
ESTRUTURA DE ARQUIVOS DO MÓDULO
================================================================================

{arvore}
"""

    partes.append(bloco_arvore)
    total_chars = len(bloco_arvore)

    arquivos = []

    for arquivo in sorted(alvo.rglob("*")):
        if arquivo.is_dir():
            continue

        if caminho_tem_pasta_ignorada(arquivo):
            continue

        if deve_ignorar_arquivo(arquivo):
            continue

        arquivos.append(arquivo)

    for arquivo in arquivos:
        bloco = ler_arquivo_para_prompt(arquivo)

        if total_chars + len(bloco) > MAX_CHARS_TOTAL:
            partes.append("""

================================================================================
AVISO
================================================================================

Alguns arquivos não foram enviados ao modelo porque o módulo ficou grande demais.
Documente com base nos arquivos enviados e registre essa limitação em "Dúvidas e Lacunas".
""")
            break

        partes.append(bloco)
        total_chars += len(bloco)

    return nome_modulo, "\n".join(partes)


# ============================================================
# Geração de documentação
# ============================================================

def montar_prompt_usuario(nome_modulo: str, caminho_alvo: Path, conteudo_modulo: str) -> str:
    rel = caminho_alvo.relative_to(PROJECT_ROOT)

    return f"""
Documente o módulo abaixo do meu sistema.

Nome do módulo:
{nome_modulo}

Caminho analisado:
{rel}

Instruções importantes:
- Documente o módulo como um conjunto.
- Não faça documentação linha por linha.
- Identifique o papel dos arquivos principais.
- Explique o fluxo geral.
- Se existirem rotas/endpoints, liste.
- Se existirem regras de negócio, liste.
- Se existirem templates, scripts JS ou estilos relacionados ao módulo, explique o papel deles no fluxo.
- Se algo não estiver claro, coloque em "Dúvidas e Lacunas".
- Não invente nomes de arquivos, rotas ou regras.
- Gere uma documentação útil para manutenção futura.
- A resposta final deve ser somente Markdown.

Conteúdo analisado:

{conteudo_modulo}
"""


def chamar_modelo(
    client: OpenAI,
    model: str,
    skill: str,
    contract: str,
    user_prompt: str,
) -> str:
    """
    Chama o modelo com retry simples para erro 429/rate limit.
    """

    max_tentativas = 4

    for tentativa in range(1, max_tentativas + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": f"{skill}\n\n{contract}",
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            )

            return response.choices[0].message.content

        except Exception as erro:
            erro_texto = str(erro)

            if "429" in erro_texto and tentativa < max_tentativas:
                espera = 30 + random.randint(1, 10)

                print(
                    f"\nModelo temporariamente limitado. "
                    f"Tentativa {tentativa}/{max_tentativas}."
                )
                print(f"Aguardando {espera} segundos antes de tentar novamente...")

                time.sleep(espera)
                continue

            raise erro

    raise RuntimeError("Falha ao chamar o modelo após várias tentativas.")


def limpar_markdown(resposta: str) -> str:
    """
    Remove cercas caso o modelo responda com ```md ou ```markdown.
    """

    texto = resposta.strip()

    if texto.startswith("```md"):
        texto = texto.removeprefix("```md").strip()

    if texto.startswith("```markdown"):
        texto = texto.removeprefix("```markdown").strip()

    if texto.startswith("```"):
        texto = texto.removeprefix("```").strip()

    if texto.endswith("```"):
        texto = texto.removesuffix("```").strip()

    return texto


def nome_arquivo_saida(nome_modulo: str) -> str:
    data = datetime.now().strftime("%Y-%m-%d_%H-%M")

    nome_limpo = (
        nome_modulo.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

    return f"{nome_limpo}_{data}.md"


def salvar_documentacao(nome_modulo: str, markdown: str) -> Path:
    DOCS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    caminho_saida = DOCS_OUTPUT_DIR / nome_arquivo_saida(nome_modulo)
    caminho_saida.write_text(markdown, encoding="utf-8")

    return caminho_saida


# ============================================================
# Programa principal
# ============================================================

def main() -> None:
    print("\n======================================")
    print(" AGENTE DOCUMENTADOR DE SISTEMA")
    print("======================================")

    print("\nRaiz do projeto detectada:")
    print(PROJECT_ROOT)

    client, model, provider_name = criar_cliente_ia()

    try:
        skill = carregar_skill()
        contract = carregar_contract()
    except FileNotFoundError as erro:
        print(f"\nERRO: {erro}")
        sys.exit(1)

    modulos = encontrar_modulos()

    if not modulos:
        print("\nNenhum módulo encontrado automaticamente.")
        print("Use a opção manual para informar uma pasta ou arquivo.")

    while True:
        if modulos:
            exibir_modulos(modulos)
            alvo = escolher_modulo(modulos)
        else:
            caminho = input(
                "\nDigite o caminho da pasta ou arquivo a partir da raiz do projeto:\n> "
            ).strip()

            alvo = PROJECT_ROOT / caminho

            if not alvo.exists():
                print(f"\nCaminho não encontrado: {alvo}")
                continue

        if alvo is None:
            print("\nEncerrando.")
            break

        print("\n======================================")
        print(" LENDO MÓDULO")
        print("======================================")
        print(f"Alvo: {alvo.relative_to(PROJECT_ROOT)}")

        nome_modulo, conteudo_modulo = ler_modulo(alvo)

        print("\n======================================")
        print(" GERANDO DOCUMENTAÇÃO")
        print("======================================")
        print(f"Provedor: {provider_name}")
        print(f"Modelo: {model}")

        user_prompt = montar_prompt_usuario(
            nome_modulo=nome_modulo,
            caminho_alvo=alvo,
            conteudo_modulo=conteudo_modulo,
        )

        try:
            resposta = chamar_modelo(
                client=client,
                model=model,
                skill=skill,
                contract=contract,
                user_prompt=user_prompt,
            )
        except Exception as erro:
            print("\nERRO ao chamar o modelo:")
            print(erro)
            continue

        markdown = limpar_markdown(resposta)
        caminho_saida = salvar_documentacao(nome_modulo, markdown)

        print("\n======================================")
        print(" DOCUMENTAÇÃO GERADA COM SUCESSO")
        print("======================================")
        print("Arquivo salvo em:")
        print(caminho_saida.relative_to(PROJECT_ROOT))

        novamente = input("\nDeseja documentar outro módulo? (s/n): ").strip().lower()

        if novamente != "s":
            print("\nEncerrando.")
            break


if __name__ == "__main__":
    main()
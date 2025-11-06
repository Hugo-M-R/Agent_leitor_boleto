"""Diagnóstico completo do Langfuse"""
import os
import sys
import time
import requests

# Configura encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

print("=" * 60)
print("DIAGNOSTICO COMPLETO DO LANGFUSE")
print("=" * 60)
print()

# 1. Verifica variáveis de ambiente
print("[1] Verificando variaveis de ambiente...")
env_vars = {
    "LANGFUSE_ENABLED": os.getenv("LANGFUSE_ENABLED"),
    "LANGFUSE_PUBLIC_KEY": os.getenv("LANGFUSE_PUBLIC_KEY"),
    "LANGFUSE_SECRET_KEY": os.getenv("LANGFUSE_SECRET_KEY"),
    "LANGFUSE_HOST": os.getenv("LANGFUSE_HOST"),
}

for key, value in env_vars.items():
    if value:
        if "KEY" in key:
            print(f"  {key}: {value[:20]}... (OK)")
        else:
            print(f"  {key}: {value} (OK)")
    else:
        print(f"  {key}: NAO CONFIGURADO (ERRO)")

print()

# 2. Testa importação do Langfuse
print("[2] Testando importacao do Langfuse...")
try:
    from langfuse import Langfuse
    print("  [OK] langfuse importado")
except Exception as e:
    print(f"  [ERRO] Nao foi possivel importar langfuse: {e}")
    sys.exit(1)

# 3. Testa inicialização do cliente
print("[3] Testando inicializacao do cliente...")
try:
    client = Langfuse()
    print("  [OK] Cliente Langfuse criado")
except Exception as e:
    print(f"  [ERRO] Nao foi possivel criar cliente: {e}")
    sys.exit(1)

# 4. Testa criação de trace
print("[4] Testando criacao de trace...")
try:
    trace = client.trace(
        name="diagnostico-teste",
        input={"teste": "diagnostico", "timestamp": time.time()},
        tags=["diagnostico", "teste"]
    )
    print("  [OK] Trace criado")
    
    # Atualiza trace
    trace.update(output={"status": "sucesso"})
    print("  [OK] Trace atualizado")
    
    # Finaliza trace
    trace.end()
    print("  [OK] Trace finalizado")
    
except Exception as e:
    print(f"  [ERRO] Nao foi possivel criar/atualizar trace: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. Testa flush (força envio)
print("[5] Testando flush (forca envio)...")
try:
    client.flush()
    print("  [OK] Flush executado (dados enviados)")
except Exception as e:
    print(f"  [ERRO] Nao foi possivel fazer flush: {e}")

# 6. Testa conectividade com o host
print("[6] Testando conectividade com Langfuse host...")
host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
try:
    response = requests.get(host, timeout=5)
    print(f"  [OK] Host acessivel: {response.status_code}")
except Exception as e:
    print(f"  [ERRO] Host nao acessivel: {e}")

# 7. Testa módulo de observabilidade
print("[7] Testando modulo de observabilidade...")
try:
    from api.observability import is_enabled, get_langfuse_client, create_trace
    print(f"  [OK] Modulo importado")
    print(f"  [OK] Langfuse habilitado: {is_enabled()}")
    
    if is_enabled():
        obs_client = get_langfuse_client()
        print(f"  [OK] Cliente obtido: {obs_client is not None}")
        
        # Testa criação via módulo
        test_trace = create_trace(
            name="teste-via-modulo",
            input_data={"teste": "via-modulo"},
            tags=["test", "modulo"]
        )
        if test_trace:
            test_trace.update(output={"status": "ok"})
            test_trace.end()
            print("  [OK] Trace criado via modulo")
            
            # Flush
            if obs_client:
                obs_client.flush()
                print("  [OK] Flush executado via modulo")
        else:
            print("  [ERRO] Trace retornou None")
    else:
        print("  [ERRO] Langfuse nao esta habilitado no modulo")
        
except Exception as e:
    print(f"  [ERRO] Erro no modulo: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("DIAGNOSTICO CONCLUIDO")
print("=" * 60)
print()
print("Aguarde 10-15 segundos e verifique no dashboard:")
print(f"  {host}")
print("  Procure por traces: 'diagnostico-teste' ou 'teste-via-modulo'")
print()
print("Se ainda nao aparecer:")
print("  1. Verifique se as chaves estao corretas no dashboard")
print("  2. Verifique se o projeto esta correto")
print("  3. Verifique firewall/proxy")
print("  4. Tente acessar o host manualmente no navegador")


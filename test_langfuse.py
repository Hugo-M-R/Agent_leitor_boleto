"""Script de teste para verificar se Langfuse está enviando traces"""
import os
import sys
import time

# Configura encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

# Verifica variáveis de ambiente
print("=== Verificando Variaveis de Ambiente ===")
print(f"LANGFUSE_ENABLED: {os.getenv('LANGFUSE_ENABLED')}")
print(f"LANGFUSE_PUBLIC_KEY: {os.getenv('LANGFUSE_PUBLIC_KEY', 'NAO CONFIGURADO')[:20]}...")
print(f"LANGFUSE_SECRET_KEY: {'CONFIGURADO' if os.getenv('LANGFUSE_SECRET_KEY') else 'NAO CONFIGURADO'}")
print(f"LANGFUSE_HOST: {os.getenv('LANGFUSE_HOST', 'NAO CONFIGURADO')}")
print()

# Testa importação e inicialização
print("=== Testando Importacao ===")
try:
    from api.observability import create_trace, create_span, is_enabled, get_langfuse_client
    print(f"[OK] Modulo importado com sucesso")
    print(f"[OK] Langfuse habilitado: {is_enabled()}")
    
    if is_enabled():
        client = get_langfuse_client()
        print(f"[OK] Cliente Langfuse: {client is not None}")
        print()
        
        # Cria um trace de teste
        print("=== Criando Trace de Teste ===")
        trace = create_trace(
            name="teste-manual-python",
            input_data={"teste": "verificacao", "timestamp": time.time()},
            tags=["test", "manual"]
        )
        
        if trace:
            print("[OK] Trace criado com sucesso")
            trace.update(output={"status": "sucesso", "mensagem": "Teste manual do Python"})
            trace.end()
            print("[OK] Trace finalizado e enviado")
            print()
            print("Aguarde 5-10 segundos e verifique no dashboard do Langfuse:")
            print("   https://us.cloud.langfuse.com")
            print("   Procure por: 'teste-manual-python'")
        else:
            print("[ERRO] Trace nao foi criado (retornou None)")
    else:
        print("[ERRO] Langfuse nao esta habilitado")
        print("   Configure no PowerShell:")
        print("   $env:LANGFUSE_ENABLED='true'")
        print("   $env:LANGFUSE_PUBLIC_KEY='sua-chave'")
        print("   $env:LANGFUSE_SECRET_KEY='sua-chave'")
        print("   $env:LANGFUSE_HOST='https://us.cloud.langfuse.com'")
        
except Exception as e:
    print(f"[ERRO] Erro: {e}")
    import traceback
    traceback.print_exc()


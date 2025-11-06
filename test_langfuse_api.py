"""Testa qual API do Langfuse está disponível"""
import os
import sys

# Configura encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

# Configura variáveis (se necessário)
if not os.getenv("LANGFUSE_ENABLED"):
    os.environ["LANGFUSE_ENABLED"] = "true"
    os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-35580a85-67ef-4f3d-adfa-0273e0794799"
    os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-6fe492bc-c63d-4d47-b24a-1df1ca6be9c1"
    os.environ["LANGFUSE_HOST"] = "https://us.cloud.langfuse.com"

print("=" * 60)
print("TESTE DE API DO LANGFUSE")
print("=" * 60)
print()

try:
    from langfuse import Langfuse
    print("[OK] Langfuse importado")
    
    client = Langfuse()
    print("[OK] Cliente criado")
    print()
    
    # Lista todos os métodos públicos
    print("Métodos disponíveis no cliente Langfuse:")
    methods = [m for m in dir(client) if not m.startswith('_')]
    for method in methods:
        attr = getattr(client, method, None)
        if callable(attr):
            print(f"  - {method}()")
        else:
            print(f"  - {method} (atributo)")
    print()
    
    # Testa métodos específicos
    print("Testando métodos específicos:")
    test_methods = ["trace", "span", "flush", "create_trace", "create_observation", "score"]
    for method_name in test_methods:
        has_method = hasattr(client, method_name)
        is_callable = callable(getattr(client, method_name, None))
        status = "[OK]" if (has_method and is_callable) else "[NAO DISPONIVEL]"
        print(f"  {method_name}: {status}")
    print()
    
    # Tenta criar um trace usando diferentes abordagens
    print("Testando criacao de trace:")
    
    # Método 1: .trace()
    if hasattr(client, "trace") and callable(getattr(client, "trace")):
        try:
            trace = client.trace(name="teste-api", input={"teste": "valor"})
            print("  [OK] client.trace() funcionou")
            print(f"  Tipo retornado: {type(trace)}")
            if hasattr(trace, "update"):
                trace.update(output={"status": "ok"})
                print("  [OK] trace.update() funcionou")
            if hasattr(trace, "end"):
                trace.end()
                print("  [OK] trace.end() funcionou")
        except Exception as e:
            print(f"  [ERRO] client.trace() falhou: {e}")
    
    # Método 2: Decorator
    try:
        @client.trace(name="teste-decorator")
        def test_func():
            return "ok"
        result = test_func()
        print("  [OK] Decorator @client.trace funcionou")
    except Exception as e:
        print(f"  [INFO] Decorator nao disponivel: {e}")
    
    # Método 3: Context manager
    try:
        with client.trace(name="teste-context"):
            pass
        print("  [OK] Context manager funcionou")
    except Exception as e:
        print(f"  [INFO] Context manager nao disponivel: {e}")
    
    # Flush
    if hasattr(client, "flush") and callable(getattr(client, "flush")):
        try:
            client.flush()
            print("  [OK] client.flush() funcionou")
        except Exception as e:
            print(f"  [ERRO] client.flush() falhou: {e}")
    
    print()
    print("=" * 60)
    print("TESTE CONCLUIDO")
    print("=" * 60)
    
except Exception as e:
    print(f"[ERRO] {e}")
    import traceback
    traceback.print_exc()


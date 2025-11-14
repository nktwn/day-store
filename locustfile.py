import base64
import random
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner

BASE_URL = "http://127.0.0.1:9000"
TEST_USERNAME = "load_test_user"
TEST_PASSWORD = "loadtest123"

product_ids = []
auth_token = ""

def create_basic_auth(username, password):
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global product_ids, auth_token

    print("=" * 60)
    print("🚀 Инициализация Load Testing...")
    print("=" * 60)

    if not isinstance(environment.runner, WorkerRunner):
        import requests

        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/users/registration",
                json={
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                    "passwordConfirmation": TEST_PASSWORD
                },
                timeout=10
            )
            if response.status_code == 200:
                print(f"✅ Тестовый пользователь создан: {TEST_USERNAME}")
            elif response.status_code == 400 and "already exists" in response.text:
                print(f"ℹ️  Тестовый пользователь уже существует: {TEST_USERNAME}")
            else:
                print(f"⚠️  Ошибка регистрации: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Не удалось создать пользователя: {e}")

        auth_token = create_basic_auth(TEST_USERNAME, TEST_PASSWORD)
        print(f"🔑 Auth токен создан")

        try:
            response = requests.get(f"{BASE_URL}/api/v1/products", timeout=10)
            if response.status_code == 200:
                data = response.json()
                product_ids = [p["id"] for p in data.get("items", [])]
                print(f"📦 Загружено {len(product_ids)} товаров для тестирования")
            else:
                print(f"⚠️  Не удалось загрузить товары: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Ошибка загрузки товаров: {e}")

        print("=" * 60)
        print("✅ Инициализация завершена. Начинаем нагрузочное тестирование...")
        print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n" + "=" * 60)
    print("🏁 Нагрузочное тестирование завершено")
    print("=" * 60)


class DayStoreUser(HttpUser):

    wait_time = between(1, 3)

    host = BASE_URL

    def on_start(self):
        self.auth_token = auth_token
        self.product_ids = product_ids

    @task(10)
    def view_catalog(self):
        with self.client.get(
                "/api/v1/products",
                catch_response=True,
                name="GET /products (catalog)"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "items" in data and len(data["items"]) > 0:
                        response.success()
                    else:
                        response.failure("Empty product list")
                except:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(8)
    def search_products(self):
        search_queries = ["Apple", "Samsung", "Dell", "Sony", "HP", "Lenovo"]
        query = random.choice(search_queries)

        with self.client.get(
                f"/api/v1/search?q={query}",
                catch_response=True,
                name="GET /search (search products)"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(6)
    def filter_by_category(self):
        categories = ["LAPTOP", "PHONE", "HEADPHONE", "SMART_WATCH", "CAMERA", "PC"]
        selected = random.sample(categories, random.randint(1, 2))
        category_param = ",".join(selected)

        with self.client.get(
                f"/api/v1/products/by-category?category={category_param}",
                catch_response=True,
                name="GET /products/by-category (filter)"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(5)
    def view_product_details(self):
        if not self.product_ids:
            return

        product_id = random.choice(self.product_ids)

        with self.client.get(
                f"/api/v1/products/{product_id}",
                headers={"Authorization": self.auth_token},
                catch_response=True,
                name="GET /products/{id} (view details)"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized (auth token issue)")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(3)
    def like_product(self):
        if not self.product_ids:
            return

        product_id = random.choice(self.product_ids)

        with self.client.post(
                f"/api/v1/products/{product_id}/like",
                headers={"Authorization": self.auth_token},
                catch_response=True,
                name="POST /products/{id}/like"
        ) as response:
            if response.status_code in [200, 400]:  # 400 если уже лайкнут
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(2)
    def get_recommendations(self):
        with self.client.get(
                "/api/v1/users/me/recommendation?limit=10",
                headers={"Authorization": self.auth_token},
                catch_response=True,
                name="GET /users/me/recommendation"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(2)
    def view_profile(self):
        with self.client.get(
                "/api/v1/users/me",
                headers={"Authorization": self.auth_token},
                catch_response=True,
                name="GET /users/me (profile)"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def purchase_product(self):
        if not self.product_ids:
            return

        product_id = random.choice(self.product_ids)

        with self.client.post(
                f"/api/v1/products/{product_id}/buy",
                headers={"Authorization": self.auth_token},
                catch_response=True,
                name="POST /products/{id}/buy (purchase)"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def view_purchase_history(self):
        with self.client.get(
                "/api/v1/users/me/purchases",
                headers={"Authorization": self.auth_token},
                catch_response=True,
                name="GET /users/me/purchases (history)"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized")
            else:
                response.failure(f"Status code: {response.status_code}")


class AnonymousUser(HttpUser):

    wait_time = between(2, 5)
    host = BASE_URL

    weight = 3

    def on_start(self):
        self.product_ids = product_ids

    @task(10)
    def browse_catalog(self):
        self.client.get("/api/v1/products", name="[Anonymous] GET /products")

    @task(5)
    def search(self):
        query = random.choice(["Apple", "Samsung", "Dell"])
        self.client.get(f"/api/v1/search?q={query}", name="[Anonymous] GET /search")

    @task(3)
    def filter_category(self):
        category = random.choice(["LAPTOP", "PHONE", "CAMERA"])
        self.client.get(
            f"/api/v1/products/by-category?category={category}",
            name="[Anonymous] GET /products/by-category"
        )

DayStoreUser.weight = 7
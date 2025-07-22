import time
import json
import datetime
import requests
from bs4 import BeautifulSoup

# Daftar kategori: Laptop, All in One & Desktop PC, Console, Phone & Tablet, Printer-&-Scanner, Aksesoris
category = "Laptop"
NAME_FILE = "data_harga_laptop.json"
WEBHOOK_URL = "https://discord.com/api/webhooks/1361521097698447360/DEcQ5vqFysxsAoW-cG5BOjof5veUVf-lI_N4YF4QPPw74ZEkr7Bj3M1QSHXHzrQn7eYL"

class ProductScraper:  
    def __init__(self):
        self.base_url = "https://www.agres.id"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Referer": "https://www.google.com",
            "Connection": "keep-alive"
        }


    # Mengambil semua data product laptop dari website --> data baru
    def scrape_product(self, category):
        attempts = 5
        for attempt in range(1, attempts + 1):
            try:
                categories_product = {"Laptop":"/c/Laptop", "All in One & Desktop PC":"/c/All-in-One-&-Desktop-PC", "Console":"/c/Console", "Phone & Tablet":"/c/Phone-&-Tablet", "Printer & Scanner":"/c/Printer-&-Scanner", "Aksesoris":"/c/Aksesoris"}
                new_list_product = []

                # Membuka halaman laptop
                url = f"{self.base_url}{categories_product[category]}"
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                # Mengambil data brand laptop dari halaman laptop agres.id
                categories = soup.find_all("a", class_="category__box")
                for i, brand in enumerate(categories, start=1):
                    link_brand = brand["href"]

                    # Membuka halaman brand laptop
                    brand_response = requests.get(link_brand, headers=self.headers, timeout=15)
                    brand_response.raise_for_status()
                    brand_soup = BeautifulSoup(brand_response.text, "html.parser")

                    # Mengambil data laptop dari halaman brand
                    list_product = brand_soup.find_all("div", class_="product-list__item")
                    for product in list_product:
                        tipe = product.find("div", class_="block__tags").getText(strip=True)
                        merk = brand.find("div", class_="category__box__image")["title"]
                        product_name = product.find("div", class_="block__title").getText(strip=True)
                        product_price = product.find("div", class_="block__price").getText(strip=True)
                        product_link = product.find("a", class_="clickable-product")["href"]
                        new_list_product.append({
                                "tipe": tipe,
                                "merk": merk,
                                "product_name": product_name,
                                "product_link": product_link,
                                "history": [{
                                    "product_price": int(product_price),
                                    "date": datetime.datetime.now().strftime("%Y-%m-%d")
                                }]
                            })

                    print(f"Progress scraping: {((i / len(categories)) * 100):.2f}%")
                    time.sleep(1)

                if new_list_product:
                    return new_list_product
                else:
                    raise ValueError("Gagal mendapatkan list product.")
                
            except Exception as e:
                print(f"Gagal scraping pada percoban ke-{attempt}.")
                if attempt < attempts:
                    print("Mencoba ulang scraping dalam 10 detik.")
                    time.sleep(10)
                else:
                    print("Gagal melakukan scraping dalam semua percobaan.")

        return []

    
class PriceComparator:
    def __init__(self, name_file):
        self.name_file = name_file
        self.old_list_product = self.__load_file_product()

    # Mengambil data json product laptop dari lokal --> data lama
    def __load_file_product(self):
        try:
            with open(self.name_file,"r") as file_obj:
                return json.load(file_obj)
        except FileNotFoundError:
            return []
        
    # Menyimpan data json hasil comparator
    def __save_file_product(self, data_file):
        with open(self.name_file,"w") as file_obj:
            json.dump(data_file, file_obj, indent=2)

    # Membandingkan harga antara list lama product dan list baru product
    def compare_lists(self, new_list_product):
        # Jika tidak ada data lama, langsung simpan semua
        if not self.old_list_product:
            self.old_list_product += new_list_product
            self.__save_file_product(self.old_list_product)
            return

        # Membuat dict sementara untuk pencarian lebih cepat
        old_product_map = {p["product_link"]: p for p in self.old_list_product}

        # Mulai membandingkan kedua list product
        for new in new_list_product:
            tipe = new["tipe"]
            name = new["product_name"]
            link = new["product_link"]
            new_price = new["history"][-1]["product_price"]
            date = new["history"][-1]["date"]

            # Menambahkan data product baru jika tidak ada di list lama
            if link not in old_product_map:
                discord.send_notification(tipe, name, link, new_price, date=date)
                self.old_list_product.append(new)
                continue
            
            old_product = old_product_map[link]
            old_price = old_product["history"][-1]["product_price"]

            # Menambahkan history ke masing masing product yang mengalami perubahan harga
            if old_price > new_price:
                old_product["history"].append(new["history"][0])
                discord.send_notification(tipe, name, link, new_price, old_price, date)
            elif old_price < new_price:
                old_product["history"].append(new["history"][0])
                discord.send_notification(tipe, name, link, new_price, old_price, date)

        # Menyimpan data yang sudah di append sebelumnya ke dalam file json
        self.__save_file_product(self.old_list_product)

class NotifierDiscord:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    # Template untuk mengirimkan webhook ke dalam server discord kita
    def send_notification(self, tipe, name, link, new_price, old_price=None, date=None):
        if old_price is None:
            title = f"🆕 Produk Baru: {name}"
            description = "Produk baru telah ditambahkan ke dalam Agres.id."
            color = 0x3498db  
            fields = [
                {"name": "🏷️ Tipe", "value": tipe, "inline": True},
                {"name": "💸 Harga", "value": f"**Rp {new_price:,.0f}**", "inline": True},
                {"name": "🔗 Link Produk", "value": f"[Klik di sini]({link})", "inline": False}
            ]
        else:
            if new_price < old_price:
                title = f"🟢 Harga Turun: {name}"
                description = "Harga mengalami penurunan."
                color = 0x2ecc71  
            elif new_price > old_price:
                title = f"🔴 Harga Naik: {name}"
                description = "Harga mengalami kenaikan."
                color = 0xe74c3c  

            fields = [
                {"name": "🏷️ Tipe", "value": tipe, "inline": True},
                {"name": "💸 Harga Sekarang", "value": f"**Rp {new_price:,.0f}**", "inline": True},
                {"name": "💰 Harga Sebelumnya", "value": f"**Rp {old_price:,.0f}**", "inline": True},
                {"name": "🔗 Link Produk", "value": f"[Klik di sini]({link})", "inline": False}
            ]

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "fields": fields,
            "footer": {
                "text": f"{date} | Dipantau oleh PriceWatcher"
            }
        }

        payload = {
            "username": "PriceWatcher",
            "embeds": [embed]
        }

        response = requests.post(self.webhook_url, json=payload)
        if response.status_code == 204:
            print(f"Notifikasi untuk '{name}' berhasil dikirim.")
        else:
            print(f"Gagal mengirim notifikasi: {response.status_code} - {response.text}")


product = ProductScraper()
comparator = PriceComparator(NAME_FILE)
discord = NotifierDiscord(WEBHOOK_URL)

scrape_list = product.scrape_product(category)
if scrape_list:
    comparator.compare_lists(scrape_list)
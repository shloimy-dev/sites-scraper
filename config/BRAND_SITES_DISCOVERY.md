# Brand website discovery (reference + sheet links)

| # | Brand | Sheet link | Reference site | Site structure | Adapter |
|---|-------|------------|----------------|----------------|---------|
| 1 | Enday | [Sheet](https://docs.google.com/spreadsheets/d/1bD7FHj9_qczskyDGWgKGsnK3aL7NnNrhKhutms_QYZU/edit?usp=sharing) | enday.com | **Shopify** – products.json | fetch_chunk + fill_and_download |
| 2 | Aurora | [Sheet](https://docs.google.com/spreadsheets/d/1kY8sVQBeBnP9zmYyAHHFZv3cJqiYmLeuBD1AjLC883Q/edit?usp=sharing) | auroragift.com | **Shopify** – products.json | fetch_chunk + fill_and_download |
| 3 | Bazic | [Sheet](https://docs.google.com/spreadsheets/d/1B4Y04L4xIdoP306mxtzEu_VMdbqdrTBXQmk_C-klgjw/edit?usp=sharing) | — | No reference site | Sheet only |
| 4 | Bruder | [Sheet](https://docs.google.com/spreadsheets/d/1c1Qh55EHhsR0Jb6ReMP2w0A3yQXU9tJNh7bV1sQGn1w/edit?usp=sharing) | brudertoys.com | **bruder.de** – shop at bruder.de/shop/en/{slug}/{5-digit item no} | scrape_brands: bruder_product_url; **cache**: run `python3 scripts/build_bruder_urls.py` to build data/fetched/bruder_product_urls.json (item_no→URL) for higher match rate |
| 5 | Razor | [Sheet](https://docs.google.com/spreadsheets/d/1Q7ltzpx-fTM4aSOcUk-Fgpvba82k00iTjNF1zhQB27I/edit?usp=sharing) | razor.com | **Custom** – product URLs: razor.com/product/{slug}/ (e.g. a2-scooter, a-scooter, ripstik-classic) | scrape_brands: razor_product_url with RAZOR_SLUG_MAP (name→slug) |
| 6 | Metal Earth | [Sheet](https://docs.google.com/spreadsheets/d/1Gwe3_D7n7qaRIAGVJ0QZgsaaZiuQUL1Y4SXtP--f4uU/edit?usp=sharing) | metalearth.com | **Custom** – product pages by slug (e.g. /concorde) | scrape_brands: metal_earth_product_url + metal_earth_parse_page (description, dimensions) |
| 7 | Winning Moves | [Sheet](https://docs.google.com/spreadsheets/d/1Xypdo82ug3HJi61bSuP6k1UJ3tBvZLKGab7Lf3PC7s4/edit?usp=sharing) | winning-moves.com | **ASP** – /product/{slug}.asp | scrape_brands: winning_moves_product_url |
| 8 | Moore | [Sheet](https://docs.google.com/spreadsheets/d/1XkOEoCVd6PtbqxNxIMcgppskB9MwHXBkKbocgRoZK3Q/edit?usp=sharing) | shop.mooretoys.com | Cart/checkout (Square); product listing TBD | Generic /products/{slug} |
| 9 | Sands | [Sheet](https://docs.google.com/spreadsheets/d/1tG-FDZNW-Mbyp0uQU1oR_nMiahKHpMEv2p8wYKgo5uM/edit?usp=sharing) | — | No website | Sheet only |
| 10 | Playkidiz | [Sheet](https://docs.google.com/spreadsheets/d/1kROK5Pn5JsIU0fsi1Jj1JJrZKIazsb5MiicITAyVX6c/edit?usp=sharing) | — | No reference site | Sheet only |
| 11 | Kent | [Sheet](https://docs.google.com/spreadsheets/d/1p9Vx569XOxoTDWUqShl3m5eSRmwIKTru/edit?usp=sharing) | kent.bike | **Shopify** – products.json | fetch_chunk + fill_and_download (when sheet downloads) |
| 12 | Gi-Go | [Sheet](https://docs.google.com/spreadsheets/d/1i18-ZOtmEqDP9_coQWkK9uD1Gg-0zTLMivzdCQfHDj8/edit?usp=sharing) | gigotoys.com.hk | **Custom** – /article/{id} | Generic /products/{slug} until we have article IDs |
| 13 | Goplay | [Sheet](https://docs.google.com/spreadsheets/d/1sZwpjm4ItQh2KCYxyBroshLdI5HJ_iFFwvilmBuFkjw/edit?usp=sharing) | Google | No product site | Sheet only |
| 14 | Rhode Island | [Sheet](https://docs.google.com/spreadsheets/d/1Wv6olci3_gta46gyBbI5UEFN0kWaoW7SXi5TNYz1V1Y/edit?usp=sharing) | rinovelty.com | **Custom** – URL {slug}~p{product_id}; search: /search?term= | scrape_brands: rhode_island_product_url (search by Lookup Code or Item Name → parse first product link) |

Already implemented: Chazak, Enday, Aurora, Colours Craft, Microkick (Shopify chunk). Atiko (sheet images only).

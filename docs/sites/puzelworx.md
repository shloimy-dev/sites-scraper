# puzelworx

- **URL:** https://toys4u.com
- **Platform:** BigCommerce (not Shopify)
- **Homepage title:** Toys 4 U - Toys Superstore - Better Toys, Better Brands
- **Homepage og:image:** 

## Recommended strategy: sheet-only extraction

- toys4u.com is BigCommerce; search returns wrong products (first result often unrelated)
- Catalog crawl would require extensive category traversal
- Extract from sheet: Name(En), UPC, Picture, Description

- Non-generic: 3/3
- Unique titles: 1, images: 0

### Sample results

- **[OK]** UPC `786138704866`
  - Title: Toys 4 U - Not Found
  - OG Desc: 
  - OG Image: 
  - Final URL: https://toys4u.com/search?q=786138704866

- **[OK]** UPC `786138704576`
  - Title: Toys 4 U - Not Found
  - OG Desc: 
  - OG Image: 
  - Final URL: https://toys4u.com/search?q=786138704576

- **[OK]** UPC `786138704378`
  - Title: Toys 4 U - Not Found
  - OG Desc: 
  - OG Image: 
  - Final URL: https://toys4u.com/search?q=786138704378

## All strategies

### search_q_upc — score 35
- Non-generic: 3/3
- Unique titles: 1, images: 0
  - [OK] 786138704866: Toys 4 U - Not Found
  - [OK] 786138704576: Toys 4 U - Not Found
  - [OK] 786138704378: Toys 4 U - Not Found

### shopify_search — score 35
- Non-generic: 3/3
- Unique titles: 1, images: 0
  - [OK] 786138704866: Toys 4 U - Not Found
  - [OK] 786138704576: Toys 4 U - Not Found
  - [OK] 786138704378: Toys 4 U - Not Found

### search_q_name — score 35
- Non-generic: 3/3
- Unique titles: 1, images: 0
  - [OK] 786138704866: Toys 4 U - Not Found
  - [OK] 786138704576: Toys 4 U - Not Found
  - [OK] 786138704378: Toys 4 U - Not Found

### direct_p — score 5
- Non-generic: 0/3
- Unique titles: 1, images: 0
  - [GEN] 786138704866: Toys 4 U - Toys Superstore - Better Toys, Better Brands
  - [GEN] 786138704576: Toys 4 U - Toys Superstore - Better Toys, Better Brands
  - [GEN] 786138704378: Toys 4 U - Toys Superstore - Better Toys, Better Brands

### search_s_upc — score 5
- Non-generic: 0/3
- Unique titles: 1, images: 0
  - [GEN] 786138704866: Toys 4 U - Toys Superstore - Better Toys, Better Brands
  - [GEN] 786138704576: Toys 4 U - Toys Superstore - Better Toys, Better Brands
  - [GEN] 786138704378: Toys 4 U - Toys Superstore - Better Toys, Better Brands

### search_s_name — score 5
- Non-generic: 0/3
- Unique titles: 1, images: 0
  - [GEN] 786138704866: Toys 4 U - Toys Superstore - Better Toys, Better Brands
  - [GEN] 786138704576: Toys 4 U - Toys Superstore - Better Toys, Better Brands
  - [GEN] 786138704378: Toys 4 U - Toys Superstore - Better Toys, Better Brands

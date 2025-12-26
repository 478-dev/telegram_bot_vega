from db import init_db, add_item

def populate():
    init_db()
    
    # Отрядные открытки - 79₽
    squads_postcards = ["Арабелла", "Арго", "Багира", "Беспокойные сердца", "Пламя", "Фиеста", "Фаворит", "Эдельвейс", "Ювента"]
    for squad in squads_postcards:
        add_item("Отрядные открытки", squad, 79, 50)
    
    # Новогодние открытки - 89₽
    ny_postcards = ["Время зажигать", "Ты - самая яркая звёздочка", "Спасибо тебе за самого лучшего друга"]
    for postcard in ny_postcards:
        add_item("Новогодние открытки", postcard, 89, 30)
    
    # Стикеры (без отряда)
    add_item("Набор смешных стикеров", None, 199, 20)
    add_item("Набор милых стикеров", None, 249, 20)
    
    # Обвесы - 249₽
    squads_accessories = ["Арабелла", "Арго", "Багира", "Беспокойные сердца", "Пламя", "Фиеста", "Фаворит", "Эдельвейс", "Ювента", "Товарищ"]
    for squad in squads_accessories:
        add_item("Обвесы", squad, 249, 15)
    
    # Пак мемологии (без отряда)
    add_item("Пак мемологии", None, 149, 25)
    
    print("✅ БД заполнена!")

if __name__ == "__main__":
    populate()

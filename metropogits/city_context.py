"""Presentation-only context for the approved structural street experiment."""


def city_context(routing):
    if routing.get('streetGrid',{}).get('version') != 'structural-streets/0.2':
        return None
    return dict(version='city-context/0.1',ground='#273039',
                majorColors=['#293641','#34333f','#293b37','#3b342e','#38323d'])

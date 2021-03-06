
/**
 * Contains all information in form of dict, that allows easily update it. 
 * Each dict contains data, event it should emit while updating and url_creation_hanler 
 * that points to url from whic this dict should take info.
 * @returns data used by application in dict format
 */
function getDataDicts() {
    return {
        actual_business: {
            is_actual: false,
            url_creation_handler: () => createUrlDependingOnStorage('/get_storage_info/id/'),
            emit: 'business_changed',
            data_processor: (data) => {
                if(data) $('service_ind').style = 'display: block'
                else $('service_ind').style = 'display: none'
                $('is_service').checked = data && data.is_service 
            },
            data: {}
        },
        existing_businesses: {
            is_actual: false,
            url_creation_handler: () => '/info_about_businesses',
            data_processor: (data) => data.map(x => x['name']),
            data: {},
            related_list: datalists.available_businesses_dl,
            emit: 'bussines_update'
        },
        current_storage_statistics: {
            is_actual: false,
            url_creation_handler: () => createUrlDependingOnStorage('/get_statistics/id/'),
            related_list: datalists.available_types_dl,
            emit: 'statistics_update',
            data: {}
        },
        orders_with_current_storage: {
            is_actual: false,
            url_creation_handler: () => createOrderUrl(),
            emit: 'pending_orders_update',
            data: {}
        },
        current_actual_order_description: {
            is_actual: false,
            emit: 'actual_order_selected',
            data: {},
            url_creation_handler: () => createExpandOrderUrl(),
            data_processor: (data) => {
                if (!data) return null
                let available_products = convertToObject('Serial number', data.available_products)
                let order_stats = data.order_stats
                let order_sides = data.order_sides
                return {
                    available_products: available_products,
                    order_sides: [order_sides],
                    order_types: Object.values(order_stats).reduce((accumulator, el) => {
                        accumulator[el['Type']] = el['Ordered']
                        return accumulator
                    }, {}),
                    order_stats: Object.values(order_stats),
                    unbinded_products: new Set(),
                    binded_products: new Set()
                }
            },
            pack: () => {
                let dict = data_dicts.current_actual_order_description.data
                return {
                    // order_stats: dict.order_stats,
                    order_types: dict.order_types,
                    unbinded_products: Array.from(dict.unbinded_products),
                    binded_products: Array.from(dict.binded_products)
                }
            }
        },
        current_history_order_description: {
            is_actual: false,
            url_creation_handler: () => createUrlDependingOnOrder('/expand_history_order/id/'),
            data: {}
        },
        producents_and_models: {
            is_actual: false,
            url_creation_handler: () => '/get_producents_and_models',
            emit: 'producent_and_models_update',
            data: {}
        }
    }
}

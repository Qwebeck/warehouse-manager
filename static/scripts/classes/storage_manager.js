class StorageManager extends Section {
    /**
     * 
     * @param {{element:Element,default_class:string,subareas:[{element:Element,hide:function()}]}} productAddingArea 
     * @param {{element:Element,default_class:string,subareas:[{element:Element,hide:function()}]}} productsArea 
     * @param {Element} toolbar 
     * @param {{}} existing_businesses 
     * @param {{}} types_on_existing_storage 
     * @param {string} active_business 
     * @param {*} source_dict - dict, where is modified flag is set
     */
    constructor(productAddingArea,
        productsArea,
        toolbar,
        existing_businesses,
        storage_statistics,
        active_business,
        productTypeManager) {
        super(
            productAddingArea,
            productsArea,
            toolbar)
        this.existing_businesses = existing_businesses
        this.storage_statistics = storage_statistics
        this.existing_types = Array.isArray(storage_statistics.data) ? storage_statistics.data.map(x => x["Tип"]) : []
        this.active_business = active_business

        this.product_type_manager = productTypeManager

        document.addEventListener(existing_businesses.emit, bussListener, false)
        document.addEventListener(storage_statistics.emit, statListener, false)
    }
    storageStatisticsUpdate(data) {
        this.existing_types = data.map(x => x["Tип"])
        updateDatalist(this.storage_statistics.related_list, this.existing_types)
        createTable(data, (row_info, _, rowNode) => {
            createActionButton(row_info,
                rowNode,
                "Tип",
                "Подробнее",
                this.expandForTypes
            )
        },
            this.rightColumn.element)
    }
    availableBusinessesUpdate(data) {
        updateDatalist(this.existing_businesses.related_list, data)
    }

    switchBusiness(e) {
        e.preventDefault()
        let new_business = e.target.active_storage.value
        
        if (this.existing_businesses.data.includes(new_business)) {
            sessionStorage.setItem('active_storage', new_business)
            for (let item in data_dicts) {
                if (item === 'existing_businesses') continue
                data_dicts[item].is_actual = false
            }
            waitingAnimation(true)
            document.dispatchEvent(data_item_modified)
        } else {
            this.addNewBusiness(new_business)
         }
    }
    expandForTypes(e) {
        e.preventDefault()
        let type = e.target.value
        productTypeManager.update(type)
        productTypeManager.show()
    }

    addNewBusiness(new_business) {
        let url = '/add_new_business'
        let data = {
            'name':new_business
        }
        let addBusiness = sendRequest(url,data,'POST')
        addBusiness.then(
            _ => {
                sessionStorage.setItem('active_storage', new_business)
                updateHeaders()
                for (let item in data_dicts) data_dicts[item].is_actual = false
                waitingAnimation(true)
                document.dispatchEvent(data_item_modified)
            }
        )
     }
    addProductToBusiness(e) {
        e.preventDefault()
        let form = e.target
        if (validateStorageForm(form) === false) {
            return
        }
        let data = formToDict(form.elements)
        let url = createUrlDependingOnStorage('/add_items_on_storage/id/')
        let post = sendRequest(url, data, "POST")
        form.reset()
        waitingAnimation(true)
        post.then(_ => {
            this.storage_statistics.is_actual = false
            document.dispatchEvent(data_item_modified)
        })
    }

}

function statListener(e) {
    storageManager.storageStatisticsUpdate(e.detail)
}
function bussListener(e) {
    storageManager.availableBusinessesUpdate(e.detail)
}
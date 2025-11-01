document.addEventListener("DOMContentLoaded", () => {
  const tabButtons = document.querySelectorAll("[data-pm-tab-target]");
  const panels = document.querySelectorAll("[data-pm-tab-panel]");

  const activateTab = (name) => {
    tabButtons.forEach((button) => {
      const isActive = button.getAttribute("data-pm-tab-target") === name;
      button.classList.toggle("is-active", isActive);
    });
    panels.forEach((panel) => {
      const isActive = panel.getAttribute("data-pm-tab-panel") === name;
      panel.classList.toggle("is-active", isActive);
    });
  };

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.getAttribute("data-pm-tab-target");
      if (!target) return;
      activateTab(target);
      const url = new URL(window.location.href);
      url.searchParams.set("tab", target);
      window.history.replaceState({}, "", url);
    });
  });

  const bareToolForm = document.querySelector(
    'form[action$="bare-tool/create/"]'
  );
  if (bareToolForm) {
    const toggleInput = bareToolForm.querySelector('input[name="create_product"]');
    const productOverrideFields = bareToolForm.querySelectorAll(
      ".pm-field-divider, .pm-product-override"
    );

    const updateProductVisibility = () => {
      const shouldShow = Boolean(toggleInput?.checked);
      productOverrideFields.forEach((element) => {
        if (shouldShow) {
          element.classList.remove("pm-hidden");
        } else {
          element.classList.add("pm-hidden");
        }
      });
    };

    // Auto-sync component fields to product fields when component fields change
    const syncField = (componentFieldName, productFieldName) => {
      const componentField = bareToolForm.querySelector(`[name="${componentFieldName}"]`);
      const productField = bareToolForm.querySelector(`[name="${productFieldName}"]`);
      
      if (componentField && productField) {
        const syncValue = () => {
          // Only sync if product field is empty and product creation is enabled
          if (toggleInput?.checked && !productField.value) {
            if (componentField.type === 'checkbox') {
              productField.checked = componentField.checked;
            } else {
              productField.value = componentField.value;
              // For select fields, trigger change event
              if (componentField.tagName === 'SELECT') {
                productField.value = componentField.value;
                productField.dispatchEvent(new Event('change', { bubbles: true }));
              }
            }
          }
        };

        componentField.addEventListener('input', syncValue);
        componentField.addEventListener('change', syncValue);
        
        // Initial sync
        syncValue();
      }
    };

    // Sync common fields: name, sku, description, brand, listingtype, motortype, image
    syncField('name', 'product_name');
    syncField('sku', 'product_sku');
    syncField('description', 'product_description');
    syncField('brand', 'product_brand');
    syncField('listingtype', 'product_listingtype');
    syncField('motortype', 'product_motortype');
    syncField('image', 'product_image');

    if (toggleInput) {
      toggleInput.addEventListener("change", () => {
        updateProductVisibility();
        // Re-sync when toggled on
        if (toggleInput.checked) {
          bareToolForm.querySelectorAll('[name^="product_"]').forEach(productField => {
            const componentName = productField.name.replace('product_', '');
            const componentField = bareToolForm.querySelector(`[name="${componentName}"]`);
            if (componentField && !productField.value) {
              if (componentField.type === 'checkbox') {
                productField.checked = componentField.checked;
              } else if (componentField.tagName === 'SELECT') {
                productField.value = componentField.value;
                productField.dispatchEvent(new Event('change', { bubbles: true }));
              } else {
                productField.value = componentField.value;
              }
            }
          });
        }
      });
      updateProductVisibility();
    }
  }

  // Batch edit selection handling
  const updateBatchButtons = (entityType) => {
    const checkboxes = document.querySelectorAll(
      `.pm-batch-checkbox[data-entity-type="${entityType}"]:checked`
    );
    const count = checkboxes.length;
    const editBtn = document.querySelector(
      `.pm-batch-edit-btn[data-target="${entityType}"]`
    );

    if (editBtn) {
      editBtn.disabled = count === 0;
      editBtn.textContent = `Edit Selected (${count})`;
    }
  };

  const selectAll = (entityType, checked) => {
    document
      .querySelectorAll(
        `.pm-batch-checkbox[data-entity-type="${entityType}"]`
      )
      .forEach((checkbox) => {
        checkbox.checked = checked;
      });
    updateBatchButtons(entityType);
  };

  // Checkbox change handlers
  document
    .querySelectorAll(".pm-batch-checkbox")
    .forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        const entityType = checkbox.getAttribute("data-entity-type");
        updateBatchButtons(entityType);
      });
    });

  // Select all buttons
  document
    .querySelectorAll(".pm-batch-select-all")
    .forEach((btn) => {
      btn.addEventListener("click", () => {
        const entityType = btn.getAttribute("data-target");
        const allChecked = Array.from(
          document.querySelectorAll(
            `.pm-batch-checkbox[data-entity-type="${entityType}"]:checked`
          )
        ).length ===
          document.querySelectorAll(
            `.pm-batch-checkbox[data-entity-type="${entityType}"]`
          ).length;
        selectAll(entityType, !allChecked);
      });
    });

  // Edit selected buttons
  document
    .querySelectorAll(".pm-batch-edit-btn")
    .forEach((btn) => {
      btn.addEventListener("click", () => {
        const entityType = btn.getAttribute("data-target");
        const checkboxes = document.querySelectorAll(
          `.pm-batch-checkbox[data-entity-type="${entityType}"]:checked`
        );
        const ids = Array.from(checkboxes)
          .map((cb) => cb.getAttribute("data-entity-id"))
          .join(",");

        if (ids) {
          const url = new URL(window.location.href);
          url.searchParams.set("tab", "batch");
          url.pathname =
            entityType === "component"
              ? "/product-management/batch/components/edit/"
              : "/product-management/batch/products/edit/";
          url.searchParams.set("ids", ids);
          window.location.href = url.toString();
        }
      });
    });

  // Bundle product selection
  const bundleProductCheckboxes = document.querySelectorAll(".pm-bundle-product-checkbox");
  const bundleSelectAllBtn = document.querySelector(".pm-bundle-select-all");
  const bundleSelectedCountBtn = document.querySelector(".pm-bundle-selected-count");
  const bundleSubmitBtn = document.getElementById("bundle-submit-btn");
  const bundleSourceProductsInput = document.querySelector("#bundle-create-form input[name='bundle-source_products']");

  const updateBundleSelection = () => {
    const checked = document.querySelectorAll(".pm-bundle-product-checkbox:checked");
    const count = checked.length;
    const productIds = Array.from(checked).map(cb => cb.getAttribute("data-product-id")).join(",");

    if (bundleSelectedCountBtn) {
      bundleSelectedCountBtn.textContent = `${count} selected`;
      bundleSelectedCountBtn.disabled = count === 0;
    }

    if (bundleSourceProductsInput) {
      bundleSourceProductsInput.value = productIds;
    }

    if (bundleSubmitBtn) {
      bundleSubmitBtn.disabled = count === 0;
    }
  };

  bundleProductCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", updateBundleSelection);
  });

  if (bundleSelectAllBtn) {
    bundleSelectAllBtn.addEventListener("click", () => {
      const allChecked = Array.from(bundleProductCheckboxes).every(cb => cb.checked);
      bundleProductCheckboxes.forEach((cb) => {
        cb.checked = !allChecked;
      });
      updateBundleSelection();
    });
  }

  // Initial update
  updateBundleSelection();
});


var EnvironmentComponent = {
  props: ["modelValue"],
  setup(props, ctx) {
    const new_key = ref("")
    const new_value = ref("")
    return { 
      environment: props.modelValue,
      new_key, new_value,
      delete_item(name){
        console.log(name)
        delete props.modelValue[name]
        ctx.emit('update:modelValue', props.modelValue)
      },
      add_item(){
        if(new_key.value){
          props.modelValue[new_key.value] = new_value.value
          new_key.value = ""
          new_value.value = ""
          ctx.emit('update:modelValue', props.modelValue)
        }
      }
    }
  },
  template: `
    <div class="q-pa-sm">
      <h5>Environment</h5>
      <q-markup-table>
        <thead>        
          <tr>
            <th class="text-left">Key</th>
            <th class="text-left">Value</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(value, name, index) in environment">
            <td>{{name}}</td>
            <td>{{value}}</td>
            <td>
              <q-btn
                color="negative"
                icon-right="delete"
                no-caps
                flat
                dense
                @click="delete_item(name)"
              />
            </td>
          </tr>
          <tr>
              <td>
                <q-input 
                  v-model="new_key" label="Key"
                />
              </td>
              <td>
                <q-input 
                  v-model="new_value" label="Value" 
                />
              </td>
              <td>
                <q-btn
                  icon-right="add"
                  no-caps
                  flat
                  dense
                  @click="add_item()"
                />
              </td>
          </tr>
        </tbody>
      </q-markup-table>
    </div>
    `
}
  
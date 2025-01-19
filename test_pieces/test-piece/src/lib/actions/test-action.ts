import { createAction, Property } from '@activepieces/pieces-framework';

export const testAction = createAction({
  name: 'test_action',
  displayName: 'Test Action',
  description: 'A test action with various property types',
  props: {
    text_input: Property.ShortText({
      displayName: 'Text Input',
      description: 'A simple text input field',
      required: true,
    }),
    number_input: Property.Number({
      displayName: 'Number Input',
      description: 'A numeric input field',
      required: false,
    }),
    checkbox: Property.Checkbox({
      displayName: 'Enable Feature',
      description: 'Toggle this feature on/off',
      required: false,
    })
  },
  async run(context) {
    return {
      success: true,
      data: context.propsValue
    };
  },
});

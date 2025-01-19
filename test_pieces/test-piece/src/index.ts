import { PieceAuth, createPiece } from '@activepieces/pieces-framework';
import { testAction } from './lib/actions/test-action';

export const testPiece = createPiece({
  displayName: 'Test Piece',
  description: 'A test piece to verify documentation generator',
  minimumSupportedRelease: '0.5.0',
  logoUrl: 'https://example.com/test-piece.png',
  categories: [],
  auth: PieceAuth.None(),
  actions: [testAction],
  authors: ["testauthor"],
  triggers: [],
});

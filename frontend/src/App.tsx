import { Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import CreateCampaign from './pages/CreateCampaign'
import Game from './pages/Game'
import Settings from './pages/Settings'
import RulesetBuilder from './pages/RulesetBuilder'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/campaigns/new" element={<CreateCampaign />} />
      <Route path="/campaigns/:id/play" element={<Game />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/rulesets/builder" element={<RulesetBuilder />} />
    </Routes>
  )
}

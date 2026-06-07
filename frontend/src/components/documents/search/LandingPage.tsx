import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import SearchLanding from "../../../assets/images/search-landing-slate.svg";
import SearchTip from "../../../assets/images/search-tips-lightbulb.svg";

type Props = {};

const Landing = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  flex-direction: column;
  gap: ${spacing.large}px;
`;

const Title = styled.div`
  font-weight: 600;
  color: ${color.textPrimary};
  margin-bottom: ${spacing.small}px;
`;

const Tips = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.xsmall}px;
`;

const TipImage = styled.img`
  width: 36px;
  height: 36px;
`;

const TipContainer = styled.div`
  display: flex;
  align-items: center;
  gap: ${spacing.xsmall}px;
  flex-direction: column;
`;

const TipTitle = styled.div`
  font-weight: 500;
  color: ${color.textPrimary};
`;

const Tip = styled.div`
  ${text.small};
  color: ${color.textSecondary};
`;

const LandingPage = (_props: Props) => {
  return (
    <Landing>
      <Title>Start typing at least 3 letters to see results</Title>
      <img src={SearchLanding} alt="Search landing" />
      <TipContainer>
        <TipImage src={SearchTip} alt="Search tip" />
        <TipTitle>Search Tips</TipTitle>
      </TipContainer>
      <Tips>
        <Tip>Use quotes to search for exact phrases.</Tip>
        <Tip>Try different keywords to improve your search.</Tip>
      </Tips>
    </Landing>
  );
};

export default LandingPage;
